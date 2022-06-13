import {
  Links,
  LiveReload,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from '@remix-run/react';
import type {
  LinksFunction,
  LoaderFunction,
  MetaFunction,
} from '@remix-run/node';
import { json } from '@remix-run/node';

import { getUser } from './session.server';
import tailwindStylesheetUrl from './styles/tailwind.css';

export const links: LinksFunction = () => [
  { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
  { rel: 'preconnect', href: 'https://fonts.gstatic.com' },
  {
    rel: 'stylesheet',
    href: 'https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;500&display=swap',
  },
  { rel: 'stylesheet', href: tailwindStylesheetUrl },
];

export const meta: MetaFunction = () => ({
  charset: 'utf-8',
  title: 'Tweetscape Experiments',
  viewport: 'width=device-width,initial-scale=1',
});

type LoaderData = {
  user: Awaited<ReturnType<typeof getUser>>;
};

export const loader: LoaderFunction = async ({ request }) =>
  json<LoaderData>({
    user: await getUser(request),
  });

export default function App() {
  return (
    <html lang='en'>
      <head>
        <Meta />
        <Links />
      </head>
      <body>
        <Outlet />
        <ScrollRestoration />
        <Scripts />
        <LiveReload />
      </body>
    </html>
  );
}
