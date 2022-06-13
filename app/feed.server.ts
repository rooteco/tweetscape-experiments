import type {
  TTweetv2Expansion,
  TTweetv2TweetField,
  TTweetv2UserField,
  TweetV2,
  UserV2,
} from 'twitter-api-v2';
import { TwitterApi, TwitterV2IncludesHelper } from 'twitter-api-v2';
import type { LoaderFunction } from '@remix-run/node';
import { autoLink } from 'twitter-text';
import { createClient } from 'redis';
import invariant from 'tiny-invariant';

import { log } from '~/log.server';

const redis = createClient({ url: process.env.REDIS_URL });
const api = new TwitterApi(process.env.TWITTER_TOKEN as string);

const MAX_AGE_SECONDS = 60 * 60 * 1; // Wait an hour before revalidating.
const USER_FIELDS: TTweetv2UserField[] = [
  'id',
  'name',
  'username',
  'verified',
  'description',
  'profile_image_url',
  'public_metrics',
  'created_at',
];
const TWEET_FIELDS: TTweetv2TweetField[] = [
  'created_at',
  'entities',
  'author_id',
  'public_metrics',
  'referenced_tweets',
];
const TWEET_EXPANSIONS: TTweetv2Expansion[] = [
  'referenced_tweets.id',
  'referenced_tweets.id.author_id',
  'entities.mentions.username',
];

export function html(text: string): string {
  return autoLink(text, {
    usernameIncludeSymbol: true,
    linkAttributeBlock(entity, attrs) {
      /* eslint-disable no-param-reassign */
      attrs.target = '_blank';
      attrs.rel = 'noopener noreferrer';
      attrs.class = 'hover:underline text-blue-500';
      /* eslint-enable no-param-reassign */
    },
  });
}

async function getTweetsFromUsernames(usernames: string[]) {
  const queries: string[] = [];
  usernames.forEach((username) => {
    const query = queries[queries.length - 1];
    if (query && `${query} OR from:${username}`.length < 512)
      queries[queries.length - 1] = `${query} OR from:${username}`;
    else queries.push(`from:${username}`);
  });
  const users: Record<string, UserV2> = {};
  const tweets: TweetV2[] = [];
  await Promise.all(
    queries.map(async (query) => {
      const res = await api.v2.search(query, {
        'max_results': 100,
        'tweet.fields': TWEET_FIELDS,
        'expansions': TWEET_EXPANSIONS,
        'user.fields': USER_FIELDS,
      });
      res.tweets.forEach((tweet) => tweets.push(tweet));
      const includes = new TwitterV2IncludesHelper(res);
      includes.users.forEach((user) => {
        users[user.id] = user;
      });
    })
  );
  return tweets.map((tweet) => ({
    ...tweet,
    html: html(tweet.text),
    author: users[tweet.author_id as string],
  }));
}

let connection: Promise<void>;
if (!redis.isOpen) connection = redis.connect();

export type LoaderData = (TweetV2 & { author: UserV2; html: string })[];

export const loader: LoaderFunction = async ({ params }) => {
  try {
    log.debug(`Verifying params.username ("${params.username}") exists...`);
    invariant(params.username, 'expected params.username');
    const username = params.username.toLowerCase().replace(/^@/, '');
    log.debug(`Checking for cached response for @${username}...`);
    await connection;
    const cachedResponse = await redis.get(username);
    if (cachedResponse) {
      log.debug(`Found cached response; sending to client...`);
      return JSON.parse(cachedResponse) as TweetV2[];
    }
    log.debug(`Fetching api.v2.userByUsername for @${username}...`);
    const { data: user } = await api.v2.userByUsername(username);
    log.debug(`Fetching api.v2.following for ${user.name}...`);
    const { data: users } = await api.v2.following(user.id);
    log.debug(`Fetching tweets from ${users.length} followed users...`);
    const tweets = await getTweetsFromUsernames(users.map((u) => u.username));
    log.debug(`Fetched ${tweets.length} tweets; caching and sending...`);
    await redis.setEx(username, MAX_AGE_SECONDS, JSON.stringify(tweets));
    return tweets;
  } catch (e) {
    log.error(`Error fetching tweets: ${JSON.stringify(e, null, 2)}`);
    throw e;
  }
};
