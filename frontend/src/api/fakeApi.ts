import { z } from "zod";

const productSchema = z.object({
  id: z.number(),
  imageUrl: z.string().url(),
  title: z.string(),
  price: z.string(),
  tags: z.array(z.string()),
  status: z.string(),
  eligibleForContent: z.boolean(),
  lastPostedDate: z.string().nullable(),
  priorityScore: z.number().min(0).max(100),
});

const backendProductSchema = z.object({
  id: z.number(),
  image_url: z.string().url().nullable(),
  title: z.string(),
  price: z.string().nullable(),
  currency_code: z.string().nullable(),
  tags: z.array(z.string()),
  status: z.string(),
  eligible_for_content: z.boolean(),
  last_posted_date: z.string().nullable(),
  priority_score: z.number().min(0).max(100),
});

const syncStatusSchema = z.object({
  status: z.enum(["idle", "running", "completed", "failed"]),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  products_synced: z.number(),
  images_synced: z.number(),
  message: z.string(),
});

const reviewItemSchema = z.object({
  id: z.number(),
  productTitle: z.string(),
  productImageUrl: z.string().url(),
  generatedAssetLabel: z.string(),
  caption: z.string(),
  platform: z.string(),
  status: z.string(),
});

const analyticsHighlightSchema = z.object({
  label: z.string(),
  value: z.string(),
  score: z.number(),
});

const worstPostSchema = z.object({
  platform: z.string(),
  external_post_url: z.string().url(),
  caption: z.string(),
  score: z.number(),
});

const analyticsDashboardSchema = z.object({
  total_published_posts: z.number(),
  total_snapshots: z.number(),
  pending_collections: z.number(),
  best_platform: analyticsHighlightSchema,
  best_product: analyticsHighlightSchema,
  best_hook: analyticsHighlightSchema,
  best_content_pillar: analyticsHighlightSchema,
  best_posting_time: analyticsHighlightSchema,
  worst_post: worstPostSchema.nullable(),
  next_action: z.string(),
});

export type Product = z.infer<typeof productSchema>;
export type ReviewItem = z.infer<typeof reviewItemSchema>;
export type SyncStatus = z.infer<typeof syncStatusSchema>;
export type AnalyticsDashboard = z.infer<typeof analyticsDashboardSchema>;

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

const products = productSchema.array().parse([
  {
    id: 1,
    imageUrl:
      "https://placehold.co/160x160/png?text=Black%20Oxford%0ARed%20Sole",
    title: "Black Oxford Red Sole Shoes",
    price: "$189",
    tags: ["Oxford", "Black", "Red sole", "Formal"],
    status: "Active",
    eligibleForContent: true,
    lastPostedDate: "2026-07-01",
    priorityScore: 94,
  },
  {
    id: 2,
    imageUrl:
      "https://placehold.co/160x160/png?text=Brown%20Monk%0AStrap",
    title: "Brown Monk Strap Leather Shoes",
    price: "$205",
    tags: ["Monk strap", "Leather", "Brown", "Formal"],
    status: "Active",
    eligibleForContent: true,
    lastPostedDate: null,
    priorityScore: 88,
  },
  {
    id: 3,
    imageUrl:
      "https://placehold.co/160x160/png?text=Oxblood%0AWholecut",
    title: "Oxblood Wholecut Oxford Shoes",
    price: "$229",
    tags: ["Wholecut", "Oxford", "Oxblood", "Premium"],
    status: "Active",
    eligibleForContent: true,
    lastPostedDate: "2026-06-24",
    priorityScore: 81,
  },
  {
    id: 4,
    imageUrl:
      "https://placehold.co/160x160/png?text=Black%20Loafers%0ARed%20Sole",
    title: "Black Loafers Red Sole",
    price: "$174",
    tags: ["Loafers", "Black", "Red sole", "Smart casual"],
    status: "Draft",
    eligibleForContent: false,
    lastPostedDate: "2026-06-17",
    priorityScore: 62,
  },
]);

const reviewQueue = reviewItemSchema.array().parse([
  {
    id: 101,
    productTitle: "Black Oxford Red Sole Shoes",
    productImageUrl:
      "https://placehold.co/160x160/png?text=Black%20Oxford%0ARed%20Sole",
    generatedAssetLabel: "Lifestyle image draft",
    caption:
      "Sharp black Oxfords with a flash of red sole energy for evening plans.",
    platform: "Instagram",
    status: "Needs review",
  },
  {
    id: 102,
    productTitle: "Brown Monk Strap Leather Shoes",
    productImageUrl:
      "https://placehold.co/160x160/png?text=Brown%20Monk%0AStrap",
    generatedAssetLabel: "Product close-up draft",
    caption:
      "Brown monk straps bring structure, polish, and just enough personality.",
    platform: "Pinterest",
    status: "Needs review",
  },
  {
    id: 103,
    productTitle: "Oxblood Wholecut Oxford Shoes",
    productImageUrl:
      "https://placehold.co/160x160/png?text=Oxblood%0AWholecut",
    generatedAssetLabel: "Studio image draft",
    caption:
      "A clean wholecut profile in oxblood for outfits that deserve a stronger finish.",
    platform: "Facebook",
    status: "Needs review",
  },
]);

const analyticsDashboard = analyticsDashboardSchema.parse({
  total_published_posts: 0,
  total_snapshots: 0,
  pending_collections: 0,
  best_platform: { label: "No platform data", value: "No data", score: 0 },
  best_product: { label: "No product data", value: "No data", score: 0 },
  best_hook: { label: "No hook data", value: "No data", score: 0 },
  best_content_pillar: { label: "No pillar data", value: "No data", score: 0 },
  best_posting_time: { label: "No posting time data", value: "No data", score: 0 },
  worst_post: null,
  next_action: "Publish posts to start collecting analytics.",
});

const latency = 120;

function delay<T>(data: T): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(data), latency);
  });
}

export async function fetchProducts(): Promise<Product[]> {
  try {
    const response = await fetch(`${apiBaseUrl}/products`);
    if (!response.ok) {
      throw new Error("Unable to load backend products.");
    }

    const backendProducts = backendProductSchema.array().parse(
      await response.json(),
    );
    return backendProducts.map((product) => ({
      id: product.id,
      imageUrl:
        product.image_url ??
        `https://placehold.co/160x160/png?text=${encodeURIComponent(product.title)}`,
      title: product.title,
      price: formatPrice(product.price, product.currency_code),
      tags: product.tags,
      status: titleCase(product.status),
      eligibleForContent: product.eligible_for_content,
      lastPostedDate: product.last_posted_date,
      priorityScore: product.priority_score,
    }));
  } catch {
    return delay(products);
  }
}

export async function fetchReviewQueue(): Promise<ReviewItem[]> {
  return delay(reviewQueue);
}

export async function syncShopifyProducts(): Promise<SyncStatus> {
  const response = await fetch(`${apiBaseUrl}/shopify/sync`, {
    method: "POST",
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail ?? "Shopify sync failed.");
  }

  return syncStatusSchema.parse(payload);
}

export async function fetchShopifySyncStatus(): Promise<SyncStatus> {
  const response = await fetch(`${apiBaseUrl}/shopify/sync-status`);
  if (!response.ok) {
    throw new Error("Unable to load sync status.");
  }

  return syncStatusSchema.parse(await response.json());
}

export async function fetchAnalyticsDashboard(): Promise<AnalyticsDashboard> {
  try {
    const response = await fetch(`${apiBaseUrl}/analytics/dashboard`);
    if (!response.ok) {
      throw new Error("Unable to load analytics dashboard.");
    }

    return analyticsDashboardSchema.parse(await response.json());
  } catch {
    return delay(analyticsDashboard);
  }
}

function formatPrice(price: string | null, currencyCode: string | null): string {
  if (!price) {
    return "No price";
  }

  if (!currencyCode) {
    return price;
  }

  return `${currencyCode} ${price}`;
}

function titleCase(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ""}${part.slice(1)}`)
    .join(" ");
}
