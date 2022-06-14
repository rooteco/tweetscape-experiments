import type { ReactNode } from 'react';
import { getMDXComponent } from 'mdx-bundler/client';
import { useLoaderData } from '@remix-run/react';
import { useMemo } from 'react';

import type { PostLoaderData } from '~/blog.server';

export { postLoader as loader } from '~/blog.server';

type PostLinkProps = { children?: ReactNode; href?: string };
function PostLink({ children, href }: PostLinkProps) {
  return (
    <a href={href} target='_blank' rel='noopener noreferrer'>
      {children}
    </a>
  );
}

export default function Post() {
  const { frontmatter, code } = useLoaderData<PostLoaderData>();
  const Component = useMemo(() => getMDXComponent(code), [code]);
  return (
    <main className='mx-auto max-w-screen-md p-4'>
      <article className='prose prose-gray relative max-w-none prose-headings:font-semibold prose-p:before:hidden prose-p:after:hidden prose-a:font-normal prose-a:text-inherit prose-blockquote:font-normal prose-blockquote:text-gray-600 prose-img:rounded-xl'>
        <div className='not-prose absolute top-0 -left-12 h-full w-px border-l-2 border-dotted border-gray-300'>
          <aside className='absolute top-0 -left-10 whitespace-nowrap italic text-gray-500 [writing-mode:vertical-rl]'>
            {new Date(frontmatter.date).toLocaleString(undefined, {
              month: 'long',
              day: 'numeric',
            })}
            <span className='my-2.5'>·</span>
            <a
              href={`https://twitter.com/${frontmatter.author}`}
              target='_blank'
              rel='noopener noreferrer'
            >
              @{frontmatter.author}
            </a>
          </aside>
        </div>
        <Component components={{ a: PostLink }} />
      </article>
    </main>
  );
}
