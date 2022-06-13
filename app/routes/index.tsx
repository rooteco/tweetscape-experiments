import { Link, useLoaderData } from '@remix-run/react';
import type { LoaderFunction } from '@remix-run/node';

type LoaderData = {
  link: string;
  date: string;
  title: string;
  summary: string;
}[];

export const loader: LoaderFunction = () => {
  const posts = [
    {
      link: '/elonmusk/feed',
      date: '6/10/2022',
      title: 'see anyone’s feed',
      summary: 'easily dive into twitter from another’s perspective',
    },
    {
      link: '/changelog',
      date: '4/20/2022',
      title: 'follow the tweetscape in realtime',
      summary: 'and reddit style time filters and even more goodies',
    },
    {
      link: '/changelog',
      date: '4/11/2022',
      title: 'performance upgrades',
      summary: 'superhuman has a 100ms rule; we have a 50ms rule',
    },
    {
      link: '/changelog',
      date: '4/3/2022',
      title: 'we just rekt everything',
      summary: 'see top articles from experts for any twitter list',
    },
    {
      link: '/changelog',
      date: '3/25/2022',
      title: 'open source twitter',
      summary: 'a few reasons why we’re building tweetscape',
    },
  ];
  return posts;
};

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
            key={post.title}
            to={post.link}
            className='group relative block border-l-2 border-gray-200 pl-6 pb-4'
          >
            <div className='absolute top-0 -left-1 -ml-px h-2 w-2 rounded-full bg-gray-200' />
            <h2 className='text-xl'>
              <span className='font-medium group-hover:underline'>
                {post.title}
              </span>
              <span className='font-normal italic text-gray-500'>
                {' '}
                ·{' '}
                {new Date(post.date).toLocaleString(undefined, {
                  dateStyle: 'short',
                })}
              </span>
            </h2>
            <p className='italic text-gray-500'>{post.summary}</p>
          </Link>
        ))}
        <div className='absolute bottom-0 -left-1 ml-px h-2 w-2 rounded-full bg-gray-200' />
      </nav>
    </main>
  );
}
