import { Link, useLoaderData } from '@remix-run/react';
import { useState } from 'react';

import type { LoaderData } from '~/feed.server';

export { loader } from '~/feed.server';

export default function Feed() {
  const tweets = useLoaderData<LoaderData>();
  const [handle, setHandle] = useState('elonmusk');
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
            <b>{tweet.author_id}: </b>
            {tweet.text}
          </li>
        ))}
      </ul>
    </main>
  );
}
