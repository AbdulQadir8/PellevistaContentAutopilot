import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchProducts,
  fetchShopifySyncStatus,
  syncShopifyProducts,
} from "../../api/fakeApi";
import { PageHeader } from "../../components/PageHeader";

export function ProductsPage() {
  const queryClient = useQueryClient();
  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: fetchProducts,
  });
  const { data: syncStatus } = useQuery({
    queryKey: ["shopify-sync-status"],
    queryFn: fetchShopifySyncStatus,
    retry: false,
  });
  const syncMutation = useMutation({
    mutationFn: syncShopifyProducts,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      await queryClient.invalidateQueries({ queryKey: ["shopify-sync-status"] });
    },
  });

  return (
    <section className="page-stack">
      <PageHeader
        eyebrow="First workflow screen"
        title="Products"
        description="Pick the products that should feed content generation and scheduling."
        action={
          <button
            className="primary-button"
            disabled={syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
            type="button"
          >
            {syncMutation.isPending ? "Syncing..." : "Sync Shopify"}
          </button>
        }
      />

      <div className="toolbar">
        <span>{products.length} products</span>
        <span>
          {syncStatus
            ? `${syncStatus.status}: ${syncStatus.products_synced} products, ${syncStatus.images_synced} images`
            : "Backend API with fake fallback"}
        </span>
      </div>
      {syncMutation.error ? (
        <div className="sync-message error">
          {syncMutation.error instanceof Error
            ? syncMutation.error.message
            : "Shopify sync failed."}
        </div>
      ) : null}

      <div className="table-wrap">
        <table className="products-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Price</th>
              <th>Tags</th>
              <th>Status</th>
              <th>Eligible</th>
              <th>Last posted</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7}>Loading products...</td>
              </tr>
            ) : (
              products.map((product) => (
                <tr key={product.id}>
                  <td>
                    <div className="product-cell">
                      <img src={product.imageUrl} alt="" />
                      <strong>{product.title}</strong>
                    </div>
                  </td>
                  <td>{product.price}</td>
                  <td>
                    <div className="tag-list">
                      {product.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <span className="status-pill">{product.status}</span>
                  </td>
                  <td>{product.eligibleForContent ? "Yes" : "No"}</td>
                  <td>{product.lastPostedDate ?? "Never"}</td>
                  <td>
                    <div className="score-cell">
                      <meter min="0" max="100" value={product.priorityScore} />
                      <span>{product.priorityScore}</span>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
