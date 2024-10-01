import { getCollection, type CollectionEntry } from 'astro:content'

export interface TagType {
  tag: string
  count: number
  pages: CollectionEntry<'blog'>[]
}

export const SiteMetadata = {
  title: 'bmw mechanic essex',
  description: 'We are specialized BMW consulting company, conveniently located in the heart of Old Town Wickford, Essex.',
  author: {
    name: 'Stefan',
    twitter: '@thebmwmechanic',
    url: 'https://izdrail.com',
    email: 'stefa@izdrail.net',
    summary: 'Senior Developer.'
  },
  org: {
    name: 'Miz Trans',
    twitter: '@thebmwmechanic',
    url: 'https://izdrail.com',
    email: 'info@hellotham.com',
    summary:
      'The bmw mechanic essex is a bmw consulting firm. We specialise in consulting in bmw repairs.'
  },
  location: 'Wickford, Essex, United Kingdom',
  latlng: [51.6085921, 0.5087559] as [number, number],
  repository: 'https://github.com/izdrail',
  buildTime: new Date()
}

export { default as Logo } from './assets/svg/astro/astro-icon-dark.svg'
export { default as LogoImage } from './assets/astro/astro-logo-dark.png'
export { default as FeaturedSVG } from './assets/svg/undraw/undraw_design_inspiration.svg'
export { default as DefaultImage } from './assets/undraw/undraw_my_feed.png'

export const NavigationLinks = [
  { name: 'Home', href: '' },
  { name: 'Manuals', href: 'manuals' },
  { name: 'Contact', href: 'contact' },
]

export const PAGE_SIZE = 6

export const GITHUB_EDIT_URL = `https://github.com/izdrail`

export const COMMUNITY_INVITE_URL = `https://astro.build/chat`

export type Sidebar = Record<string, { text: string; link: string }[]>

export async function getPosts() {
  const posts = await getCollection('blog', ({ data }) => {
    return data.draft !== true
  })
  return posts.sort((a, b) =>
    a.data.pubDate && b.data.pubDate ? +b.data.pubDate - +a.data.pubDate : 0
  )
}
export async function getManuals() {
  const posts = await getCollection('manuals', ({ data }) => {
    return data.draft !== true
  })
  return posts.sort((a, b) =>
      a.data.pubDate && b.data.pubDate ? +b.data.pubDate - +a.data.pubDate : 0
  )
}
