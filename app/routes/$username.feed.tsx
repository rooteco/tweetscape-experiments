import { useLoaderData, useParams } from '@remix-run/react';
import { useState } from 'react';

import type { LoaderData } from '~/feed.server';
import { TimeAgo } from '~/components/timeago';

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
      <main className='my-8 mx-auto max-w-screen-sm'>
        {tweets
          .sort(
            (a, b) =>
              new Date(b.created_at as string).valueOf() -
              new Date(a.created_at as string).valueOf()
          )
          .map((tweet) => (
            <div className='mx-2 my-6 flex' key={tweet.id}>
              <img
                className='h-12 w-12 rounded-full border border-gray-300 bg-gray-100'
                alt=''
                src={tweet.author.profile_image_url}
              />
              <article key={tweet.id} className='ml-2.5 flex-1'>
                <header>
                  <h3>
                    <a
                      href={`https://twitter.com/${tweet.author.username}`}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='mr-1 font-medium hover:underline'
                    >
                      {tweet.author.name}
                    </a>
                    <a
                      href={`https://twitter.com/${tweet.author.username}`}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='text-sm text-gray-500'
                    >
                      @{tweet.author.username}
                    </a>
                    <span className='mx-1 text-sm text-gray-500'>·</span>
                    <a
                      href={`https://twitter.com/${tweet.author.username}/status/${tweet.id}`}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='text-sm text-gray-500 hover:underline'
                    >
                      <TimeAgo
                        locale='en_short'
                        datetime={new Date(tweet.created_at ?? new Date())}
                      />
                    </a>
                  </h3>
                </header>
                <p
                  dangerouslySetInnerHTML={{ __html: tweet.html ?? tweet.text }}
                />
              </article>
            </div>
          ))}
      </main>
    </>
  );
}
