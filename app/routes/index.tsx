import { Link, useLoaderData } from '@remix-run/react';

import type { IndexLoaderData } from '~/blog.server';

export { indexLoader as loader } from '~/blog.server';

export default function Index() {
  const posts = useLoaderData<IndexLoaderData>();
  return (
    <main className='flex max-h-screen flex-col items-center justify-center px-6 lg:flex-row'>
      <section>
        <div>
          <h1 className='text-2xl font-medium sm:text-4xl sm:pt-4 pt-8'>
            tweetscape<i className='ml-1 text-blue-500'>experiments</i>
          </h1>
          <p className='italic text-gray-500'>
            explorations on better social media exploration
          </p>
        </div>
      </section>
      <nav className='overflow-auto max-h-screen relative mt-12 lg:mt-16 lg:ml-16'>
        {posts.map((post) => (
          <Link
            key={post.frontmatter.title}
            to={post.path}
            className='group relative block border-l-2 border-dotted border-gray-300 pl-6 pb-4'
          >
            <div className='absolute top-0 -left-1 -ml-px h-2 w-2 rounded-full bg-gray-300' />
            <h2 className='text-xl'>
              <span className='font-medium group-hover:underline'>
                {post.frontmatter.title}
              </span>
              <span className='font-normal italic text-gray-500'>
                {' '}
                ·{' '}
                {new Date(post.frontmatter.date).toLocaleString(undefined, {
                  dateStyle: 'short',
                })}
              </span>
            </h2>
            <p className='italic text-gray-500'>{post.frontmatter.summary}</p>
          </Link>
        ))}
        <div className='absolute bottom-0 -left-1 ml-px h-2 w-2 rounded-full bg-gray-200' />
      </nav>
    </main>
  );
}
