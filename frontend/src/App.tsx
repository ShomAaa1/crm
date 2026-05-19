import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { HomePage } from "@/pages/HomePage";
import { CatalogPage } from "@/pages/catalog/CatalogPage";
import { PartDetailsPage } from "@/pages/catalog/PartDetailsPage";
import { UsersPage } from "@/pages/admin/UsersPage";
import { CategoriesPage } from "@/pages/admin/CategoriesPage";
import { PartsPage } from "@/pages/admin/PartsPage";
import { CartPage } from "@/pages/cart/CartPage";
import { MyRequestsPage } from "@/pages/requests/MyRequestsPage";
import { RequestDetailsPage } from "@/pages/requests/RequestDetailsPage";
import { ManagerRequestsPage } from "@/pages/manager/RequestsPage";
import { ProposalDetailsPage } from "@/pages/proposals/ProposalDetailsPage";
import { ProposalsListPage } from "@/pages/proposals/ProposalsListPage";
import { useAuthStore } from "@/store/auth";

export default function App() {
  const init = useAuthStore((s) => s.init);
  const initialized = useAuthStore((s) => s.initialized);

  useEffect(() => {
    init();
  }, [init]);

  if (!initialized) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        Загрузка…
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomePage />} />

        {/* Каталог — доступен всем залогиненным */}
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="catalog/:id" element={<PartDetailsPage />} />

        {/* Корзина — только client */}
        <Route
          path="cart"
          element={
            <ProtectedRoute roles={["client"]}>
              <CartPage />
            </ProtectedRoute>
          }
        />

        {/* Заявки клиента */}
        <Route
          path="requests"
          element={
            <ProtectedRoute roles={["client"]}>
              <MyRequestsPage />
            </ProtectedRoute>
          }
        />
        {/* Детали заявки доступны всем причастным — проверка на бэкенде */}
        <Route path="requests/:id" element={<RequestDetailsPage />} />

        {/* Заявки для менеджера / руководителя / админа */}
        <Route
          path="manager/requests"
          element={
            <ProtectedRoute roles={["manager", "head", "admin"]}>
              <ManagerRequestsPage />
            </ProtectedRoute>
          }
        />

        {/* Коммерческие предложения */}
        <Route path="proposals" element={<ProposalsListPage />} />
        <Route path="proposals/:id" element={<ProposalDetailsPage />} />

        {/* Управление каталогом — manager/head/admin */}
        <Route
          path="admin/categories"
          element={
            <ProtectedRoute roles={["manager", "head", "admin"]}>
              <CategoriesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/parts"
          element={
            <ProtectedRoute roles={["manager", "head", "admin"]}>
              <PartsPage />
            </ProtectedRoute>
          }
        />

        {/* Пользователи — только admin */}
        <Route
          path="admin/users"
          element={
            <ProtectedRoute roles={["admin"]}>
              <UsersPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
