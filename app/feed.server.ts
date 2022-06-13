import type {
  TTweetv2Expansion,
  TTweetv2TweetField,
  TTweetv2UserField,
  TweetV2,
} from 'twitter-api-v2';
import type { LoaderFunction } from '@remix-run/node';
import { TwitterApi } from 'twitter-api-v2';
import invariant from 'tiny-invariant';

import { log } from '~/log.server';

const api = new TwitterApi(process.env.TWITTER_TOKEN as string);

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

async function getTweetsFromUsernames(usernames: string[]): Promise<TweetV2[]> {
  const queries: string[] = [];
  usernames.forEach((username) => {
    const query = queries[queries.length - 1];
    if (query && `${query} OR from:${username}`.length < 512)
      queries[queries.length - 1] = `${query} OR from:${username}`;
    else queries.push(`from:${username}`);
  });
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
    })
  );
  return tweets;
}

export type LoaderData = TweetV2[];

export const loader: LoaderFunction = async ({ params }) => {
  log.debug(`Verifying params.username ("${params.username}") exists...`);
  invariant(params.username, 'expected params.username');
  log.debug(`Fetching api.v2.userByUsername for @${params.username}...`);
  const { data: user } = await api.v2.userByUsername(params.username);
  log.debug(`Fetching api.v2.following for ${user.name}...`);
  const { data: users } = await api.v2.following(user.id);
  log.debug(`Fetching tweets from ${users.length} followed users...`);
  const tweets = await getTweetsFromUsernames(users.map((u) => u.username));
  log.debug(`Fetched ${tweets.length} tweets; sending to client...`);
  return tweets;
};
