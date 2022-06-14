import fs from 'fs/promises';
import { resolve } from 'path';

import type { LoaderFunction } from '@remix-run/node';
import { bundleMDX } from 'mdx-bundler';
import invariant from 'tiny-invariant';
import { json } from '@remix-run/node';

import { log } from '~/log.server';

export const BLOG_DIRECTORY = '../blog';

export type Meta = {
  date: string;
  author: string;
  title: string;
  summary: string;
};
export type IndexLoaderData = {
  frontmatter: Meta;
  code: string;
  path: string;
}[];

export const indexLoader: LoaderFunction = async () => {
  const cwd = resolve(__dirname, BLOG_DIRECTORY);
  const filenames = await fs.readdir(cwd);
  const files = filenames.map((f) => resolve(cwd, f));
  log.info(`Parsing markdown for ${files.length} files...`);
  const posts = await Promise.all(
    files.map((file) => bundleMDX<Meta>({ file, cwd }))
  );
  return json<IndexLoaderData>(
    posts
      .map((post, idx) => ({
        ...post,
        path: filenames[idx].replace('.mdx', '').replace(/\./g, '/'),
      }))
      .sort(
        (a, b) =>
          new Date(b.frontmatter.date).valueOf() -
          new Date(a.frontmatter.date).valueOf()
      )
  );
};

export type PostLoaderData = { frontmatter: Meta; code: string };

export const postLoader: LoaderFunction = async ({ params }) => {
  invariant(params.post, 'expected params.post');
  const cwd = resolve(__dirname, BLOG_DIRECTORY);
  const file = resolve(cwd, `blog.${params.post}.mdx`);
  const post = await bundleMDX<Meta>({ file, cwd });
  return json<PostLoaderData>(post);
};
