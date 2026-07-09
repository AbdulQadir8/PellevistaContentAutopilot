import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { DashboardLayout } from "./app/DashboardLayout";
import { AnalyticsPage } from "./features/analytics/AnalyticsPage";
import { AssetsPage } from "./features/assets/AssetsPage";
import { CalendarPage } from "./features/content-calendar/CalendarPage";
import { ProductsPage } from "./features/products/ProductsPage";
import { ReviewQueuePage } from "./features/review-queue/ReviewQueuePage";
import { SettingsPage } from "./features/settings/SettingsPage";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route index element={<Navigate to="/products" replace />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/review-queue" element={<ReviewQueuePage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/assets" element={<AssetsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
