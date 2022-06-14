import { Link, useLoaderData } from '@remix-run/react';

import type { LoaderData } from '~/blog.server';

export { loader } from '~/blog.server';

export default function Index() {
  const posts = useLoaderData<LoaderData>();
  return (
    <main className='flex h-screen items-center justify-center'>
      <section>
        <div>
          <h1 className='text-4xl font-medium'>
            tweetscape<i className='ml-1 text-blue-500'>experiments</i>
          </h1>
          <p className='italic text-gray-500'>
            explorations on better social media exploration
          </p>
        </div>
      </section>
      <nav className='relative ml-16'>
        {posts.map((post) => (
          <Link
            key={post.frontmatter.title}
            to={post.path}
            className='group relative block border-l-2 border-gray-200 pl-6 pb-4'
          >
            <div className='absolute top-0 -left-1 -ml-px h-2 w-2 rounded-full bg-gray-200' />
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
