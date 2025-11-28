"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import styles from "./AnnotatorInterface.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5005";

interface Thumbnail {
  index: number;
  filename: string;
  date_display: string;
  sort_date: [number, number, number];
  original_path: string;
}

interface FarmData {
  farm_id: string;
  image_count: number;
  thumbnails: Thumbnail[];
  selected_index?: number | null;
}

export function AnnotatorInterface() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [assignedFarms, setAssignedFarms] = useState<string[]>([]);
  const [currentFarmIndex, setCurrentFarmIndex] = useState(0);
  const [currentFarm, setCurrentFarm] = useState<string | null>(null);
  const [farmData, setFarmData] = useState<FarmData | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{
    text: string;
    type: "success" | "error" | "info";
  } | null>(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("token");
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  const showMessage = useCallback(
    (text: string, type: "success" | "error" | "info" = "info") => {
      setMessage({ text, type });
      setTimeout(() => setMessage(null), 4000);
    },
    []
  );

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");

    if (!token || !userStr) {
      router.push("/");
      return;
    }

    const userData = JSON.parse(userStr);
    if (userData.role === "admin") {
      router.push("/admin");
      return;
    }

    setUser(userData);
    loadAssignedFarms();
    loadStats();
  }, []);

  useEffect(() => {
    if (assignedFarms.length > 0 && currentFarmIndex < assignedFarms.length) {
      const farmId = assignedFarms[currentFarmIndex];
      setCurrentFarm(farmId);
      loadFarmData(farmId);
    }
  }, [currentFarmIndex, assignedFarms]);

  const loadAssignedFarms = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/annotator/assigned-farms`, {
        headers: getAuthHeaders(),
      });
      const data = await response.json();

      if (response.ok) {
        const farmIds = data.farm_ids || [];
        const farmStatuses = data.farms || [];
        setAssignedFarms(farmIds);

        if (farmIds.length > 0) {
          // Find first uncompleted farm
          let firstUncompletedIndex = farmStatuses.findIndex(
            (f: any) => !f.completed
          );

          // If all completed, start from beginning
          if (firstUncompletedIndex === -1) {
            firstUncompletedIndex = 0;
          }

          setCurrentFarmIndex(firstUncompletedIndex);
        }
      }
    } catch (error) {
      console.error("Error loading assigned farms:", error);
      showMessage("Error loading assigned farms", "error");
    }
  };

  const loadFarmData = async (farmId: string) => {
    setLoading(true);
    setSelectedImageIndex(null);

    try {
      const response = await fetch(`${API_BASE}/api/annotator/farm/${farmId}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Failed to load farm data");
      }

      const data: FarmData = await response.json();
      setFarmData(data);

      if (typeof data.selected_index === "number" && data.selected_index >= 0) {
        setSelectedImageIndex(data.selected_index);
      }
    } catch (error: any) {
      console.error("Error loading farm data:", error);
      showMessage(error.message || "Error loading farm data", "error");
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/annotator/stats`, {
        headers: getAuthHeaders(),
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error loading stats:", error);
    }
  };

  const handleSave = async () => {
    if (!currentFarm || selectedImageIndex === null || !farmData) {
      showMessage("Please select an image first", "error");
      return;
    }

    setSaving(true);

    try {
      const selectedImage = farmData.thumbnails[selectedImageIndex];
      const response = await fetch(`${API_BASE}/api/annotator/save`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          farm_id: currentFarm,
          selected_image: selectedImage.filename,
          image_path: selectedImage.original_path,
          total_images: farmData.image_count,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save annotation");
      }

      showMessage(`Saved annotation for farm ${currentFarm}`, "success");
      await loadStats();

      // Move to next farm
      if (currentFarmIndex < assignedFarms.length - 1) {
        setCurrentFarmIndex(currentFarmIndex + 1);
      } else {
        showMessage("All farms completed! Great job!", "success");
      }
    } catch (error: any) {
      console.error("Error saving annotation:", error);
      showMessage(error.message || "Failed to save annotation", "error");
    } finally {
      setSaving(false);
    }
  };

  const handlePrevious = () => {
    if (currentFarmIndex > 0) {
      setCurrentFarmIndex(currentFarmIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentFarmIndex < assignedFarms.length - 1) {
      setCurrentFarmIndex(currentFarmIndex + 1);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/");
  };

  const handleKeyPress = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter" && selectedImageIndex !== null) {
        handleSave();
      } else if (e.key === "ArrowLeft") {
        handlePrevious();
      } else if (e.key === "ArrowRight") {
        handleNext();
      }
    },
    [selectedImageIndex, currentFarmIndex, assignedFarms]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [handleKeyPress]);

  if (!user) {
    return <div className={styles.loading}>Loading...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>🌾 Farm Annotation Tool</h1>
          <div className={styles.headerActions}>
            <span className={styles.userName}>Welcome, {user.username}</span>
            <button onClick={handleLogout} className={styles.logoutButton}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {stats && (
        <div className={styles.statsBar}>
          <div className={styles.statsContent}>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>Assigned:</span>
              <span className={styles.statValue}>{stats.assigned}</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>Completed:</span>
              <span className={styles.statValue}>{stats.completed}</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>Remaining:</span>
              <span className={styles.statValue}>{stats.remaining}</span>
            </div>
            <div className={styles.progressWrapper}>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${stats.progress}%` }}
                />
              </div>
              <span className={styles.progressText}>{stats.progress}%</span>
            </div>
          </div>
        </div>
      )}

      {message && (
        <div className={`${styles.message} ${styles[message.type]}`}>
          {message.text}
        </div>
      )}

      <main className={styles.content}>
        {assignedFarms.length === 0 ? (
          <div className={styles.noFarms}>
            <h2>No farms assigned yet</h2>
            <p>
              Please contact your administrator to assign farms for annotation.
            </p>
          </div>
        ) : loading ? (
          <div className={styles.loading}>Loading farm data...</div>
        ) : farmData ? (
          <>
            <div className={styles.farmHeader}>
              <h2>
                Farm {currentFarm} ({currentFarmIndex + 1} of{" "}
                {assignedFarms.length})
              </h2>
              <p>Select the image that shows the harvest-ready state</p>
            </div>

            <div className={styles.imageGrid}>
              {farmData.thumbnails.map((thumb, idx) => (
                <div
                  key={idx}
                  className={`${styles.imageCard} ${
                    selectedImageIndex === idx ? styles.selected : ""
                  }`}
                  onClick={() => setSelectedImageIndex(idx)}
                >
                  <img
                    src={`${API_BASE}/thumbs/${currentFarm}/${thumb.filename}`}
                    alt={thumb.date_display}
                    loading="lazy"
                  />
                  <div className={styles.imageInfo}>
                    <span className={styles.imageDate}>
                      {thumb.date_display}
                    </span>
                    {selectedImageIndex === idx && (
                      <span className={styles.selectedBadge}>✓ Selected</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className={styles.actions}>
              <button
                onClick={handlePrevious}
                disabled={currentFarmIndex === 0}
                className={styles.navButton}
              >
                ← Previous Farm
              </button>

              <button
                onClick={handleSave}
                disabled={selectedImageIndex === null || saving}
                className={styles.saveButton}
              >
                {saving ? "Saving..." : "Save Selection (Enter)"}
              </button>

              <button
                onClick={handleNext}
                disabled={currentFarmIndex >= assignedFarms.length - 1}
                className={styles.navButton}
              >
                Next Farm →
              </button>
            </div>

            <div className={styles.helpText}>
              <p>
                <strong>Keyboard shortcuts:</strong> Use arrow keys (← →) to
                navigate between farms, press Enter to save your selection.
              </p>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
