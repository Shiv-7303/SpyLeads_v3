/**
 * SpyLeads Instagram Profile Scraper
 * Apify Actor - src/main.js
 *
 * Strategy:
 *  1. Open Instagram hashtag page via Playwright
 *  2. Intercept XHR/fetch calls to capture Instagram's internal GraphQL
 *     responses (most reliable — avoids brittle DOM scraping)
 *  3. Collect post author usernames from intercepted data
 *  4. Visit each profile page, intercept the profile JSON response
 *  5. Extract: username, followers, bio, email, category, location, profile_url
 *  6. Apply follower filters
 *  7. Push to Apify dataset
 */

import { Actor } from 'apify';
import { PlaywrightCrawler, Dataset } from 'crawlee';

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

/**
 * Random int between min and max (inclusive)
 */
function randomDelay(minMs = 3000, maxMs = 8000) {
  return Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
}

/**
 * Sleep for given ms
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Extract email-like strings from bio text
 */
function extractEmailFromBio(bio = '') {
  const match = bio.match(/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/);
  return match ? match[0] : null;
}

/**
 * Build the hashtag page URL (using API endpoint for stability)
 */
function hashtagUrl(tag) {
  return `https://www.instagram.com/api/v1/tags/web_info/?tag_name=${encodeURIComponent(tag)}`;
}

/**
 * Build a profile API URL from username
 */
function profileUrl(username) {
  return `https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`;
}

// ─────────────────────────────────────────────
// MAIN ACTOR
// ─────────────────────────────────────────────

await Actor.init();

const input = await Actor.getInput();

const {
  query = '',
  type = 'hashtag',
  maxResults = 50,
  minFollowers = 0,
  maxFollowers = 0,
  sessionCookie = '',
  phase1ProxyType = 'datacenter',
} = input || {};

if (!query) {
  throw new Error('Input "query" is required. Pass a hashtag without the # symbol.');
}

console.log(`\n🚀 SpyLeads Actor Starting`);
console.log(`   Query     : #${query}`);
console.log(`   Max       : ${maxResults}`);
console.log(`   Followers : ${minFollowers || 'any'} – ${maxFollowers || 'any'}`);
console.log(`   Phase 1 PX: ${phase1ProxyType.toUpperCase()}`);
console.log(``);

// ─────────────────────────────────────────────
// PROXY SETUP (this is why other scrapers work!)
// Instagram blocks datacenter IPs instantly.
// Apify's residential proxies rotate real IPs.
// ─────────────────────────────────────────────
const proxyConfigResidential = await Actor.createProxyConfiguration({
  groups: ['RESIDENTIAL'],
  countryCode: 'IN',
});
const proxyConfigDatacenter = await Actor.createProxyConfiguration(); // Default datacenter

console.log(`   Proxy Setup: Residential configured for Phase 2.`);

// Collected usernames from hashtag page
const collectedUsernames = new Set();

// Final results
const results = [];

// Track start time to allow graceful exits before hard timeout
const ACTOR_START_TIME = Date.now();
const MAX_RUNTIME_MS = 220 * 1000; // 220 seconds (Leaves 20s buffer for the 240s backend timeout)

// ─────────────────────────────────────────────
// PHASE 1: COLLECT USERNAMES FROM HASHTAG PAGE
// ─────────────────────────────────────────────

console.log(`[Phase 1] Opening hashtag page: #${query}`);

const hashtagCrawler = new PlaywrightCrawler({
  maxConcurrency: 1,
  maxRequestRetries: 1, // Fail fast on Phase 1
  navigationTimeoutSecs: 30,
  requestHandlerTimeoutSecs: 60,
  proxyConfiguration: phase1ProxyType === 'residential' ? proxyConfigResidential : proxyConfigDatacenter,

  launchContext: {
    launchOptions: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
      ],
    },
  },

  // Intercept Instagram's internal API calls to capture post data
  preNavigationHooks: [
    async ({ page }) => {
      if (sessionCookie) {
        await page.context().addCookies([{
          name: 'sessionid',
          value: sessionCookie,
          domain: '.instagram.com',
          path: '/'
        }]);
      }

      // Set headers required for the API endpoint
      await page.setExtraHTTPHeaders({
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest'
      });

      // No interception needed since we load the API directly
    },
  ],


  async requestHandler({ page, request, response }) {
    console.log(`[Phase 1] API Page loaded: ${request.url}`);

    try {
      if (response) {
        const rawText = await response.text();
        // DEBUG: print snippet of response
        console.log(`[Phase 1] Response snippet: ${rawText.substring(0, 150)}`);
        
        const data = JSON.parse(rawText);
        parseUsernamesFromGraphQL(data, collectedUsernames, 300);
        
        if (collectedUsernames.size < 150) {
            const cursor = findCursor(data);
            if (cursor) {
                const baseUrl = request.url.split('&max_id=')[0];
                const nextUrl = `${baseUrl}&max_id=${cursor}`;
                console.log(`[Phase 1] Paginating... Next cursor: ${cursor}`);
                await hashtagCrawler.addRequests([nextUrl]);
            }
        }
      }
    } catch (e) {
      console.log(`[Phase 1] Error extracting JSON: ${e.message}`);
    }

    console.log(`[Phase 1] Done. Collected ${collectedUsernames.size} usernames so far.`);
  },
});

await hashtagCrawler.run([hashtagUrl(query)]);

// ─────────────────────────────────────────────
// PHASE 2: VISIT EACH PROFILE AND EXTRACT DATA
// ─────────────────────────────────────────────

const usernameList = [...collectedUsernames]; // Take all collected usernames to find enough matches

if (usernameList.length === 0) {
  console.log('⚠️  No usernames collected. Instagram may have blocked or changed selectors.');
  await Dataset.pushData({
    error: "phase1_failed",
    reason: "ip_blocked",
    proxy_used: phase1ProxyType
  });
  await Actor.exit();
}

console.log(`\n[Phase 2] Found ${usernameList.length} total usernames. Filtering to find exactly ${maxResults} matches...`);

const profileCrawler = new PlaywrightCrawler({
  maxConcurrency: 1,
  maxRequestRetries: 2,
  navigationTimeoutSecs: 30,
  requestHandlerTimeoutSecs: 60,
  proxyConfiguration: proxyConfigResidential,

  launchContext: {
    launchOptions: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
      ],
    },
  },

  preNavigationHooks: [
    async ({ page }) => {
      if (sessionCookie) {
        await page.context().addCookies([{
          name: 'sessionid',
          value: sessionCookie,
          domain: '.instagram.com',
          path: '/'
        }]);
      }

      // Set headers required for the API endpoint
      await page.setExtraHTTPHeaders({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
      });

      // No need to intercept anymore, we navigate directly to the API
    },
  ],

  async requestHandler({ page, request, response }) {
    if (results.length >= maxResults) return; // Exit early if we met the quota
    
    // Graceful Exit: Stop if we are about to hit the timeout, saving partial results
    if (Date.now() - ACTOR_START_TIME > MAX_RUNTIME_MS) {
        console.log(`[Phase 2] ⏳ Time limit approaching. Exiting gracefully to save ${results.length} found profiles.`);
        return;
    }

    const username = request.userData.username;
    console.log(`[Phase 2] Checking Profile: @${username}`);

    // Polite delay between profiles — increased slightly to avoid blocks on high concurrency
    await sleep(randomDelay(4000, 10000));
    
    let profileData = null;
    try {
        if (response) {
            const rawText = await response.text();
            const parsed = JSON.parse(rawText);
            if (parsed.data && parsed.data.user) {
                 profileData = parsed.data.user;
            }
        }
    } catch (e) {
        console.log(`[Phase 2] JSON error for @${username}: ${e.message}`);
    }

    // Parse the profile object from the API response
    const actualProfileUrl = `https://www.instagram.com/${username}/`;
    const profile = extractProfileFields(username, profileData, actualProfileUrl);

    if (!profile) {
      console.log(`[Phase 2] ⚠️  Could not extract data for @${username}`);
      return;
    }

    if (results.length >= maxResults) return;

    // Apply follower filters
    if (minFollowers > 0 && profile.followers < minFollowers) {
        console.log(`[Phase 2] Skipped @${username} (${profile.followers} followers - below min ${minFollowers})`);
        return;
    }
    if (maxFollowers > 0 && profile.followers > maxFollowers) {
        console.log(`[Phase 2] Skipped @${username} (${profile.followers} followers - above max ${maxFollowers})`);
        return;
    }

    results.push(profile);
    await Dataset.pushData(profile);
    console.log(`[Phase 2] ✅ @${username} matched! (${profile.followers} followers). Target: ${results.length}/${maxResults}`);
  },
});

// Build request list from collected usernames
const profileRequests = usernameList.map((username) => ({
  url: profileUrl(username),
  userData: { username },
}));

await profileCrawler.run(profileRequests);

// ─────────────────────────────────────────────
// DONE
// ─────────────────────────────────────────────

console.log(`\n✅ SpyLeads Actor Complete`);
console.log(`   Profiles extracted : ${results.length}`);
console.log(`   Hashtag queried    : #${query}`);

await Actor.exit();


// ─────────────────────────────────────────────
// PARSE HELPERS
// ─────────────────────────────────────────────

/**
 * Walk a GraphQL response object recursively and pull out
 * any "username" strings into collectedUsernames.
 * Instagram's response structure changes often — recursive search
 * is more robust than hardcoded paths.
 */
function parseUsernamesFromGraphQL(obj, set, limit) {
  if (!obj || typeof obj !== 'object') return;
  if (set.size >= limit) return;

  if (obj.username && typeof obj.username === 'string') {
    set.add(obj.username);
  }

  for (const val of Object.values(obj)) {
    if (set.size >= limit) break;
    if (typeof val === 'object') {
      parseUsernamesFromGraphQL(val, set, limit);
    }
  }
}

/**
 * Finds the pagination cursor recursively
 */
function findCursor(obj) {
  if (typeof obj !== 'object' || !obj) return null;
  if (obj.next_max_id && typeof obj.next_max_id === 'string') return obj.next_max_id;
  if (obj.end_cursor && typeof obj.end_cursor === 'string') return obj.end_cursor;
  for (const key of Object.keys(obj)) {
    const res = findCursor(obj[key]);
    if (res) return res;
  }
  return null;
}

/**
 * Given raw data from Instagram (any shape) and a username,
 * return a normalized profile object.
 */
function extractProfileFields(username, rawData, pageUrl) {
  // Walk the object tree looking for the user node
  const userNode = findUserNode(rawData, username);

  if (!userNode) {
    return {
      username,
      followers: 0,
      bio: null,
      email: null,
      category: null,
      location: null,
      profile_url: pageUrl,
      is_verified: null,
    };
  }

  const followers =
    userNode.follower_count ??
    userNode.edge_followed_by?.count ??
    userNode.followers?.count ??
    0;

  const bio = userNode.biography || userNode.bio || null;
  const email = extractEmailFromBio(bio || '') || userNode.public_email || null;
  const category = userNode.category_name || userNode.category || null;
  const location = userNode.city_name || userNode.location || null;

  return {
    username: userNode.username || username,
    followers,
    bio,
    email,
    category,
    location,
    profile_url: `https://www.instagram.com/${username}/`,
    is_verified: userNode.is_verified || false,
  };
}

/**
 * Recursively find a node in obj that looks like an Instagram user
 * (has a "username" matching the expected username).
 */
function findUserNode(obj, username, depth = 0) {
  if (!obj || typeof obj !== 'object' || depth > 12) return null;

  if (
    obj.username === username &&
    (obj.follower_count !== undefined ||
      obj.edge_followed_by !== undefined ||
      obj.biography !== undefined)
  ) {
    return obj;
  }

  for (const val of Object.values(obj)) {
    const found = findUserNode(val, username, depth + 1);
    if (found) return found;
  }

  return null;
}
