"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import styles from "./AdminDashboard.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5005";

interface User {
  id: string;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface Assignment {
  id: string;
  user_id: string;
  username: string;
  farm_ids: string[];
  assigned_count: number;
  completed_count: number;
  assigned_at: string;
  status: string;
}

interface Stats {
  total_users: number;
  total_farms: number;
  assigned_farms: number;
  unassigned_farms: number;
  total_annotations: number;
  total_assignments: number;
  user_stats: Array<{
    username: string;
    assigned: number;
    completed: number;
    progress: number;
  }>;
}

export function AdminDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"stats" | "users" | "assignments">(
    "stats"
  );
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showCreateAssignment, setShowCreateAssignment] = useState(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("token");
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");

    if (!token || !userStr) {
      router.push("/");
      return;
    }

    const userData = JSON.parse(userStr);
    if (userData.role !== "admin") {
      router.push("/annotate");
      return;
    }

    setUser(userData);
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === "stats") {
        const response = await fetch(`${API_BASE}/api/admin/stats`, {
          headers: getAuthHeaders(),
        });
        const data = await response.json();
        setStats(data);
      } else if (activeTab === "users") {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
          headers: getAuthHeaders(),
        });
        const data = await response.json();
        setUsers(data);
      } else if (activeTab === "assignments") {
        const response = await fetch(`${API_BASE}/api/admin/assignments`, {
          headers: getAuthHeaders(),
        });
        const data = await response.json();
        setAssignments(data);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/");
  };

  const handleDownload = async (format: "csv" | "json") => {
    try {
      const response = await fetch(
        `${API_BASE}/api/admin/download?format=${format}`,
        {
          headers: getAuthHeaders(),
        }
      );

      if (format === "csv") {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `annotations_${
          new Date().toISOString().split("T")[0]
        }.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: "application/json",
        });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `annotations_${
          new Date().toISOString().split("T")[0]
        }.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error("Error downloading annotations:", error);
      alert("Failed to download annotations");
    }
  };

  const deleteUser = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user?")) return;

    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error("Error deleting user:", error);
    }
  };

  const deleteAssignment = async (assignmentId: string) => {
    if (!confirm("Are you sure you want to delete this assignment?")) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/admin/assignments/${assignmentId}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        }
      );

      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error("Error deleting assignment:", error);
    }
  };

  const handleClearAllAnnotations = async () => {
    if (
      !confirm(
        "⚠️ Are you sure you want to delete ALL annotations? This cannot be undone!"
      )
    ) {
      return;
    }

    if (
      !confirm(
        "This will permanently delete all annotation data. Are you absolutely sure?"
      )
    ) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/admin/annotations/clear`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Failed to clear annotations");
      }

      alert("✅ All annotations have been deleted successfully");
      loadData();
    } catch (error) {
      console.error("Clear error:", error);
      alert("❌ Failed to clear annotations");
    }
  };

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>🌾 Farm Annotation - Admin Dashboard</h1>
          <div className={styles.headerActions}>
            <span className={styles.userName}>Welcome, {user?.username}</span>
            <button onClick={handleLogout} className={styles.logoutButton}>
              Logout
            </button>
          </div>
        </div>
      </header>

      <nav className={styles.tabs}>
        <button
          className={activeTab === "stats" ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab("stats")}
        >
          📊 Statistics
        </button>
        <button
          className={activeTab === "users" ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab("users")}
        >
          👥 Users
        </button>
        <button
          className={
            activeTab === "assignments" ? styles.tabActive : styles.tab
          }
          onClick={() => setActiveTab("assignments")}
        >
          📋 Assignments
        </button>
      </nav>

      <main className={styles.content}>
        {loading ? (
          <div className={styles.loading}>Loading...</div>
        ) : (
          <>
            {activeTab === "stats" && stats && (
              <div className={styles.statsView}>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <div className={styles.statIcon}>👥</div>
                    <div className={styles.statValue}>{stats.total_users}</div>
                    <div className={styles.statLabel}>Total Users</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statIcon}>🚜</div>
                    <div className={styles.statValue}>{stats.total_farms}</div>
                    <div className={styles.statLabel}>Total Farms</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statIcon}>✅</div>
                    <div className={styles.statValue}>
                      {stats.assigned_farms}
                    </div>
                    <div className={styles.statLabel}>Assigned Farms</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statIcon}>📝</div>
                    <div className={styles.statValue}>
                      {stats.total_annotations}
                    </div>
                    <div className={styles.statLabel}>Total Annotations</div>
                  </div>
                </div>

                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <h2>User Progress</h2>
                    <div className={styles.actionButtons}>
                      <button
                        onClick={handleClearAllAnnotations}
                        className={styles.dangerButton}
                        title="Delete all annotations"
                      >
                        🗑️ Clear All Annotations
                      </button>
                    </div>
                  </div>
                  <div className={styles.tableContainer}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Username</th>
                          <th>Assigned</th>
                          <th>Completed</th>
                          <th>Progress</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.user_stats.map((stat) => (
                          <tr key={stat.username}>
                            <td>{stat.username}</td>
                            <td>{stat.assigned}</td>
                            <td>{stat.completed}</td>
                            <td>
                              <div className={styles.progressContainer}>
                                <div
                                  className={styles.progressBar}
                                  style={{ width: `${stat.progress}%` }}
                                />
                                <span className={styles.progressText}>
                                  {stat.progress.toFixed(1)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className={styles.section}>
                  <h2>Download Annotations</h2>
                  <div className={styles.downloadButtons}>
                    <button
                      onClick={() => handleDownload("csv")}
                      className={styles.downloadButton}
                    >
                      📥 Download CSV
                    </button>
                    <button
                      onClick={() => handleDownload("json")}
                      className={styles.downloadButton}
                    >
                      📥 Download JSON
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "users" && (
              <div className={styles.usersView}>
                <div className={styles.sectionHeader}>
                  <h2>User Management</h2>
                  <button
                    onClick={() => setShowCreateUser(true)}
                    className={styles.createButton}
                  >
                    + Create User
                  </button>
                </div>

                <div className={styles.tableContainer}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Full Name</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td>{user.username}</td>
                          <td>{user.email || "-"}</td>
                          <td>{user.full_name || "-"}</td>
                          <td>
                            <span
                              className={
                                user.role === "admin"
                                  ? styles.roleAdmin
                                  : styles.roleUser
                              }
                            >
                              {user.role}
                            </span>
                          </td>
                          <td>
                            <span
                              className={
                                user.is_active
                                  ? styles.statusActive
                                  : styles.statusInactive
                              }
                            >
                              {user.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td>
                            {new Date(user.created_at).toLocaleDateString()}
                          </td>
                          <td>
                            {user.role !== "admin" && (
                              <button
                                onClick={() => deleteUser(user.id)}
                                className={styles.deleteButton}
                              >
                                Delete
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {showCreateUser && (
                  <CreateUserModal
                    onClose={() => setShowCreateUser(false)}
                    onSuccess={() => {
                      setShowCreateUser(false);
                      loadData();
                    }}
                    getAuthHeaders={getAuthHeaders}
                  />
                )}
              </div>
            )}

            {activeTab === "assignments" && (
              <div className={styles.assignmentsView}>
                <div className={styles.sectionHeader}>
                  <h2>Farm Assignments</h2>
                  <div className={styles.assignmentInfo}>
                    {stats && (
                      <div className={styles.infoBox}>
                        <span className={styles.infoLabel}>
                          Unassigned Farms:
                        </span>
                        <span className={styles.infoValue}>
                          {stats.unassigned_farms}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={() => setShowCreateAssignment(true)}
                      className={styles.createButton}
                    >
                      + Create Assignment
                    </button>
                  </div>
                </div>

                <div className={styles.tableContainer}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Assigned Farms</th>
                        <th>Completed</th>
                        <th>Progress</th>
                        <th>Assigned Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assignments.map((assignment) => (
                        <tr key={assignment.id}>
                          <td>{assignment.username}</td>
                          <td>{assignment.assigned_count}</td>
                          <td>{assignment.completed_count}</td>
                          <td>
                            <div className={styles.progressContainer}>
                              <div
                                className={styles.progressBar}
                                style={{
                                  width: `${
                                    (assignment.completed_count /
                                      assignment.assigned_count) *
                                    100
                                  }%`,
                                }}
                              />
                              <span className={styles.progressText}>
                                {(
                                  (assignment.completed_count /
                                    assignment.assigned_count) *
                                  100
                                ).toFixed(1)}
                                %
                              </span>
                            </div>
                          </td>
                          <td>
                            {new Date(
                              assignment.assigned_at
                            ).toLocaleDateString()}
                          </td>
                          <td>
                            <button
                              onClick={() => deleteAssignment(assignment.id)}
                              className={styles.deleteButton}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {showCreateAssignment && (
                  <CreateAssignmentModal
                    onClose={() => setShowCreateAssignment(false)}
                    onSuccess={() => {
                      setShowCreateAssignment(false);
                      loadData();
                    }}
                    getAuthHeaders={getAuthHeaders}
                    users={users}
                  />
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

// Create User Modal Component
function CreateUserModal({
  onClose,
  onSuccess,
  getAuthHeaders,
}: {
  onClose: () => void;
  onSuccess: () => void;
  getAuthHeaders: () => any;
}) {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    email: "",
    full_name: "",
    role: "annotator",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/admin/users`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to create user");
      }

      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.modal}>
      <div className={styles.modalContent}>
        <h3>Create New User</h3>
        {error && <div className={styles.error}>{error}</div>}
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label>Username *</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) =>
                setFormData({ ...formData, username: e.target.value })
              }
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Password *</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
            />
          </div>
          <div className={styles.formGroup}>
            <label>Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) =>
                setFormData({ ...formData, full_name: e.target.value })
              }
            />
          </div>
          <div className={styles.formGroup}>
            <label>Role</label>
            <select
              value={formData.role}
              onChange={(e) =>
                setFormData({ ...formData, role: e.target.value })
              }
            >
              <option value="annotator">Annotator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className={styles.modalActions}>
            <button
              type="button"
              onClick={onClose}
              className={styles.cancelButton}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={styles.submitButton}
            >
              {loading ? "Creating..." : "Create User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Create Assignment Modal Component
function CreateAssignmentModal({
  onClose,
  onSuccess,
  getAuthHeaders,
  users,
}: {
  onClose: () => void;
  onSuccess: () => void;
  getAuthHeaders: () => any;
  users: User[];
}) {
  const [selectedUser, setSelectedUser] = useState("");
  const [farmCount, setFarmCount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const count = parseInt(farmCount);
      if (isNaN(count) || count <= 0) {
        throw new Error("Please enter a valid number greater than 0");
      }

      const response = await fetch(`${API_BASE}/api/admin/assignments`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          user_id: selectedUser,
          farm_count: count,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to create assignment");
      }

      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const annotators = users.filter((u) => u.role === "annotator");

  return (
    <div className={styles.modal}>
      <div className={styles.modalContent}>
        <h3>Create Farm Assignment</h3>
        {error && <div className={styles.error}>{error}</div>}
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label>Select User *</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              required
            >
              <option value="">-- Select a user --</option>
              {annotators.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </option>
              ))}
            </select>
          </div>
          <div className={styles.formGroup}>
            <label>Number of Farms to Assign *</label>
            <input
              type="number"
              value={farmCount}
              onChange={(e) => setFarmCount(e.target.value)}
              placeholder="Enter number of farms (e.g., 10)"
              min="1"
              required
            />
            <small>System will automatically assign unassigned farms</small>
          </div>
          <div className={styles.modalActions}>
            <button
              type="button"
              onClick={onClose}
              className={styles.cancelButton}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={styles.submitButton}
            >
              {loading ? "Creating..." : "Create Assignment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
