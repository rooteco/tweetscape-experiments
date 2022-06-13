import { Link, useLoaderData } from '@remix-run/react';
import type { LoaderFunction } from '@remix-run/node';
import invariant from 'tiny-invariant';
import { useState } from 'react';

export type LoaderData = { id: string; author: string; text: string }[];

export const loader: LoaderFunction = async ({ params }) => {
  invariant(params.username, 'expected params.username');
  return [];
};

export default function Feed() {
  const tweets = useLoaderData<LoaderData>();
  const [handle, setHandle] = useState('@elonmusk');
  return (
    <main>
      <div>
        <input
          type='text'
          placeholder='Enter any Twitter handle'
          value={handle}
          onChange={(evt) => setHandle(evt.currentTarget.value)}
        />
        <Link
          to={`/${encodeURIComponent(handle)}/feed`}
          className='ml-2 inline-block bg-black p-2 text-white'
        >
          See their feed
        </Link>
      </div>
      <ul>
        {tweets.map((tweet) => (
          <li key={tweet.id}>
            <b>{tweet.author}: </b>
            {tweet.text}
          </li>
        ))}
      </ul>
    </main>
  );
}
