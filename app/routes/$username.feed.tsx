import { useLoaderData, useParams } from '@remix-run/react';
import { useState } from 'react';

import type { LoaderData } from '~/feed.server';

export { loader } from '~/feed.server';

export default function Feed() {
  const { username } = useParams();
  const tweets = useLoaderData<LoaderData>();
  const [handle, setHandle] = useState(username ?? 'elonmusk');
  return (
    <>
      <form
        method='get'
        className='sticky top-2 my-8 mx-auto flex max-w-sm'
        action={`/${encodeURIComponent(handle)}/feed`}
      >
        <input
          type='text'
          placeholder='Enter any Twitter handle'
          value={handle}
          onChange={(evt) => setHandle(evt.currentTarget.value)}
          className='flex-1 rounded border-2 border-black px-2 py-1'
        />
        <button
          type='submit'
          className='ml-2 inline-block rounded border-2 border-black bg-black px-2 py-1 text-white'
        >
          See their feed
        </button>
      </form>
      <ul className='my-8 mx-auto max-w-screen-sm'>
        {tweets.map((tweet) => (
          <li key={tweet.id} className='mx-2 my-6'>
            <b>{tweet.author_id}: </b>
            {tweet.text}
          </li>
        ))}
      </ul>
    </>
  );
}
