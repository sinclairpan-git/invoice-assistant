import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import "antd/dist/reset.css";

import { createAppRouter } from "./app/router";
import { AppProviders } from "./app/providers";
import "./styles.css";


const router = createAppRouter();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </React.StrictMode>,
);
