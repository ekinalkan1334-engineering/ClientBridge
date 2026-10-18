
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const REFRESH_INTERVAL = 15000;

function formatAmount(amount) {
  const numericAmount = Number(amount);

  if (!Number.isFinite(numericAmount)) {
    return "—";
  }

  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
  }).format(numericAmount);
}

function App() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchOrders = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/orders`);

      if (!response.ok) {
        throw new Error(`Orders API error: ${response.status}`);
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error("Invalid orders response");
      }

      setOrders(data);
      setError("");
    } catch {
      setError(
        "Siparişler yüklenemedi. Backend sunucusunu ve bağlantıyı kontrol et."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(`${API_URL}/health/ready`, {
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Health API error: ${response.status}`);
      }

      const data = await response.json();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      clearTimeout(timeoutId);
      setHealthLoading(false);
    }
  }, []);

  const refreshDashboard = useCallback(async () => {
    setRefreshing(true);

    try {
      await Promise.all([fetchOrders(), fetchHealth()]);
    } finally {
      setRefreshing(false);
    }
  }, [fetchOrders, fetchHealth]);

  useEffect(() => {
    refreshDashboard();

    const interval = setInterval(() => {
      refreshDashboard();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [refreshDashboard]);

  const stats = [
    {
      label: "Total Orders",
      value: orders.length,
      change: "All received orders",
      icon: "▤",
    },
    {
      label: "Synchronized",
      value: orders.filter((order) => order.status === "SYNCED").length,
      change: "Successfully delivered",
      icon: "✓",
    },
    {
      label: "Pending Orders",
      value: orders.filter(
        (order) =>
          order.status === "PENDING" ||
          order.status === "PROCESSING"
      ).length,
      change: "Waiting to be processed",
      icon: "◷",
    },
    {
      label: "Failed Orders",
      value: orders.filter((order) => order.status === "FAILED").length,
      change: "Need your attention",
      icon: "!",
    },
  ];

  const databaseHealthy = health?.checks?.database === true;
  const crmHealthy = health?.checks?.crm === true;
  const workerHealthy = health?.checks?.worker === true;

  function getHealthLabel(isHealthy) {
    if (healthLoading) return "Checking...";
    if (!health) return "No connection";
    return isHealthy ? "Healthy" : "Unavailable";
  }

  function getHealthClass(isHealthy) {
    if (healthLoading || !health) return "neutral";
    return isHealthy ? "healthy" : "neutral";
  }

  function getWorkerLabel() {
    if (healthLoading) return "Checking...";
    if (!health) return "No connection";
    return workerHealthy ? "Running" : "Unavailable";
  }

  function getWorkerClass() {
    if (healthLoading || !health) return "neutral";
    return workerHealthy ? "healthy" : "neutral";
  }

  function getCrmLabel() {
    if (healthLoading) return "Checking...";
    if (!health) return "No connection";
    return crmHealthy ? "Reachable" : "Unavailable";
  }

  function scrollToSection(sectionId) {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <span className="brand-letter">C</span>
            <span className="brand-spark">✦</span>
          </div>

          <div className="brand-copy">
            <h2>ClientBridge</h2>
            <span>INTEGRATION PLATFORM</span>
          </div>
        </div>

        <div className="menu-label">WORKSPACE</div>

        <nav className="navigation">
          <a
            className="nav-item active"
            href="#dashboard"
            onClick={(event) => {
              event.preventDefault();
              scrollToSection("dashboard");
            }}
          >
            <span>▦</span>
            Dashboard
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon">i</div>
            <strong>Need help?</strong>
            <p>
              Review your integration status and system activity.
            </p>
          </div>

          <div className="profile">
            <div className="avatar">RB</div>
            <div className="profile-copy">
              <strong>Rachel Borders</strong>
              <span>Workspace Admin</span>
            </div>
            <span className="profile-menu">···</span>
          </div>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> Dashboard
          </div>

          <div className="topbar-right">
            <span className="environment">
              <span className="green-dot" /> Development
            </span>
            <div className="top-avatar">CB</div>
          </div>
        </header>

        <section className="page-heading">
          <div>
            <div className="eyebrow">OVERVIEW</div>
            <h1>Dashboard</h1>
            <p>
              Monitor your orders, integrations, and synchronization health.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={refreshDashboard}
            disabled={refreshing}
          >
            ↻ <span>{refreshing ? "Refreshing..." : "Refresh"}</span>
          </button>
        </section>

        {error && (
          <div role="alert" className="error-message">
            {error}
          </div>
        )}

        <section className="stats-grid">
          {stats.map((stat, index) => (
            <article className="stat-card" key={stat.label}>
              <div className={`stat-icon icon-${index}`}>
                {stat.icon}
              </div>
              <div className="stat-label">{stat.label}</div>
              <div className="stat-value">
                {loading ? "..." : stat.value}
              </div>
              <div className="stat-foot">{stat.change}</div>
            </article>
          ))}
        </section>

        <section className="system-section" id="systems">
          <div className="section-heading">
            <div>
              <h2>System Health</h2>
              <p>Current status of your connected services</p>
            </div>

            <span className="live-label">
              <span className="green-dot" />
              Auto-refresh every 15 seconds
            </span>
          </div>

          <div className="system-grid">
            <article className="system-card">
              <div className="system-icon database-icon">▤</div>
              <div className="system-info">
                <strong>PostgreSQL</strong>
                <span>Database connection</span>
              </div>

              <span
                className={`status-pill ${getHealthClass(databaseHealthy)}`}
              >
                <span />
                {getHealthLabel(databaseHealthy)}
              </span>
            </article>

            <article className="system-card">
              <div className="system-icon crm-icon">⇄</div>
              <div className="system-info">
                <strong>Mock CRM</strong>
                <span>External service</span>
              </div>

              <span
                className={`status-pill ${getHealthClass(crmHealthy)}`}
              >
                <span />
                {getCrmLabel()}
              </span>
            </article>

            <article className="system-card">
              <div className="system-icon worker-icon">⚙</div>
              <div className="system-info">
                <strong>Background Worker</strong>
                <span>Order processing</span>
              </div>

              <span className={`status-pill ${getWorkerClass()}`}>
                <span />
                {getWorkerLabel()}
              </span>
            </article>
          </div>
        </section>

        <section className="orders-section" id="orders">
          <div className="section-heading orders-heading">
            <div>
              <h2>Recent Orders</h2>
              <p>Track the latest order synchronization activity</p>
            </div>

            <button
              className="secondary-button"
              onClick={() => scrollToSection("orders-table")}
            >
              View all orders <span>→</span>
            </button>
          </div>

          <div className="table-wrap">
            <table id="orders-table">
              <thead>
                <tr>
                  <th>ORDER ID</th>
                  <th>CUSTOMER</th>
                  <th>AMOUNT</th>
                  <th>STATUS</th>
                  <th>RETRIES</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="5">Loading orders...</td>
                  </tr>
                ) : error && orders.length === 0 ? (
                  <tr>
                    <td colSpan="5">Orders could not be loaded.</td>
                  </tr>
                ) : orders.length === 0 ? (
                  <tr>
                    <td colSpan="5">No orders found.</td>
                  </tr>
                ) : (
                  orders.map((order) => (
                    <tr key={order.order_id}>
                      <td className="order-id">{order.order_id}</td>
                      <td>{order.customer_email}</td>
                      <td className="amount">
                        {formatAmount(order.total_amount)}
                      </td>
                      <td>
                        <span
                          className={`order-status ${String(
                            order.status
                          ).toLowerCase()}`}
                        >
                          <span className="status-dot" />
                          {order.status}
                        </span>
                      </td>
                      <td>{order.retry_count}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            <span>
              {loading
                ? "Loading..."
                : `Showing ${orders.length} real orders`}
            </span>
            <span>ClientBridge · Local dashboard</span>
          </div>
        </section>

        <section className="activity-section" id="activity">
          <div className="section-heading">
            <div>
              <h2>Activity Overview</h2>
              <p>A quick summary of the current order activity</p>
            </div>
          </div>

          <div className="activity-card">
            <div className="activity-item">
              <span className="activity-marker success-marker">✓</span>
              <div>
                <strong>{stats[1].value} synchronized orders</strong>
                <p>Orders successfully delivered to the connected CRM.</p>
              </div>
            </div>

            <div className="activity-item">
              <span className="activity-marker pending-marker">◷</span>
              <div>
                <strong>{stats[2].value} pending orders</strong>
                <p>Orders waiting to be processed by the background worker.</p>
              </div>
            </div>

            <div className="activity-item">
              <span className="activity-marker failed-marker">!</span>
              <div>
                <strong>{stats[3].value} failed orders</strong>
                <p>Orders that may need attention or another retry.</p>
              </div>
            </div>
          </div>
        </section>

        <footer className="footer">
          <span>© 2026 ClientBridge</span>
          <span>Order Integration &amp; Sync Platform</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
