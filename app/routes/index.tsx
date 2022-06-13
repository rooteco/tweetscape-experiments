import type { LoaderFunction } from '@remix-run/node';
import { useLoaderData } from '@remix-run/react';

type LoaderData = { id: string; title: string; summary: string }[];

export const loader: LoaderFunction = async () => {
  const posts = [
    {
      id: 'see-anyones-feed',
      title: 'See anyones feed',
      summary: 'Easily see the world from anothers perspective',
    },
  ];
  return posts;
};

export default function Index() {
  const posts = useLoaderData<LoaderData>();
  return (
    <main className='flex items-center justify-center'>
      <section>
        <div>
          <h1>
            tweetscape <i>experiments</i>
          </h1>
          <p>explorations on better social media exploration</p>
        </div>
      </section>
      <section>
        <ul>
          {posts.map((post) => (
            <li key={post.id} className='bl relative pl-4'>
              <h2>{post.title}</h2>
              <p>{post.summary}</p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
