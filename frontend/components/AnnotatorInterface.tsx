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
  thumbnails_2024: Thumbnail[];
  thumbnails_2025: Thumbnail[];
  selected_index_2024?: number | null;
  selected_index_2025?: number | null;
}

export function AnnotatorInterface() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [assignedFarms, setAssignedFarms] = useState<string[]>([]);
  const [currentFarmIndex, setCurrentFarmIndex] = useState(0);
  const [currentFarm, setCurrentFarm] = useState<string | null>(null);
  const [farmData, setFarmData] = useState<FarmData | null>(null);
  const [selectedImageIndex2024, setSelectedImageIndex2024] = useState<
    number | null
  >(null);
  const [selectedImageIndex2025, setSelectedImageIndex2025] = useState<
    number | null
  >(null);
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
    setSelectedImageIndex2024(null);
    setSelectedImageIndex2025(null);

    try {
      const response = await fetch(`${API_BASE}/api/annotator/farm/${farmId}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Failed to load farm data");
      }

      const data: FarmData = await response.json();
      setFarmData(data);

      if (
        typeof data.selected_index_2024 === "number" &&
        data.selected_index_2024 >= 0
      ) {
        setSelectedImageIndex2024(data.selected_index_2024);
      }
      if (
        typeof data.selected_index_2025 === "number" &&
        data.selected_index_2025 >= 0
      ) {
        setSelectedImageIndex2025(data.selected_index_2025);
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
    if (!currentFarm || !farmData) {
      showMessage("Please wait for farm data to load", "error");
      return;
    }

    // At least one image should be selected
    if (selectedImageIndex2024 === null && selectedImageIndex2025 === null) {
      showMessage(
        "Please select at least one image (from 2024 or 2025)",
        "error"
      );
      return;
    }

    setSaving(true);

    try {
      const selectedImage2024 =
        selectedImageIndex2024 !== null
          ? farmData.thumbnails_2024[selectedImageIndex2024]
          : null;
      const selectedImage2025 =
        selectedImageIndex2025 !== null
          ? farmData.thumbnails_2025[selectedImageIndex2025]
          : null;

      const response = await fetch(`${API_BASE}/api/annotator/save`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          farm_id: currentFarm,
          selected_image_2024: selectedImage2024?.filename || null,
          image_path_2024: selectedImage2024?.original_path || null,
          selected_image_2025: selectedImage2025?.filename || null,
          image_path_2025: selectedImage2025?.original_path || null,
          total_images: farmData.image_count,
          total_images_2024: farmData.thumbnails_2024.length,
          total_images_2025: farmData.thumbnails_2025.length,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save annotation");
      }

      showMessage(`Annotation saved for farm ${currentFarm}`, "success");
      await loadStats();

      // Move to next farm
      if (currentFarmIndex < assignedFarms.length - 1) {
        setCurrentFarmIndex(currentFarmIndex + 1);
      } else {
        showMessage(
          "All assigned farms have been annotated successfully",
          "success"
        );
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
      if (
        e.key === "Enter" &&
        (selectedImageIndex2024 !== null || selectedImageIndex2025 !== null)
      ) {
        handleSave();
      } else if (e.key === "ArrowLeft") {
        handlePrevious();
      } else if (e.key === "ArrowRight") {
        handleNext();
      }
    },
    [
      selectedImageIndex2024,
      selectedImageIndex2025,
      currentFarmIndex,
      assignedFarms,
    ]
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
          <h1>Farm Harvest Annotation System</h1>
          <div className={styles.headerActions}>
            <span className={styles.userName}>{user.username}</span>
            <button onClick={handleLogout} className={styles.logoutButton}>
              Sign Out
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
            <h2>No Farm Assignments</h2>
            <p>
              You currently have no farms assigned. Please contact your system
              administrator for farm assignments.
            </p>
          </div>
        ) : loading ? (
          <div className={styles.loading}>Loading farm data...</div>
        ) : farmData ? (
          <>
            <div className={styles.farmHeader}>
              <h2>
                Farm ID: {currentFarm} ({currentFarmIndex + 1} of{" "}
                {assignedFarms.length})
              </h2>
              <p>
                Please select one representative image from each year (2024 and
                2025) that best demonstrates the harvest-ready state.
              </p>
            </div>

            {/* 2024 Images Section */}
            <div className={styles.yearSection}>
              <h3 className={styles.yearHeader}>
                2024 Images ({farmData.thumbnails_2024.length} available)
              </h3>
              {farmData.thumbnails_2024.length > 0 ? (
                <div className={styles.imageGrid}>
                  {farmData.thumbnails_2024.map((thumb, idx) => (
                    <div
                      key={`2024-${idx}`}
                      className={`${styles.imageCard} ${
                        selectedImageIndex2024 === idx ? styles.selected : ""
                      }`}
                      onClick={() => setSelectedImageIndex2024(idx)}
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
                        {selectedImageIndex2024 === idx && (
                          <span className={styles.selectedBadge}>
                            ✓ Selected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.noImages}>No 2024 images available</div>
              )}
            </div>

            {/* 2025 Images Section */}
            <div className={styles.yearSection}>
              <h3 className={styles.yearHeader}>
                2025 Images ({farmData.thumbnails_2025.length} available)
              </h3>
              {farmData.thumbnails_2025.length > 0 ? (
                <div className={styles.imageGrid}>
                  {farmData.thumbnails_2025.map((thumb, idx) => (
                    <div
                      key={`2025-${idx}`}
                      className={`${styles.imageCard} ${
                        selectedImageIndex2025 === idx ? styles.selected : ""
                      }`}
                      onClick={() => setSelectedImageIndex2025(idx)}
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
                        {selectedImageIndex2025 === idx && (
                          <span className={styles.selectedBadge}>
                            ✓ Selected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.noImages}>No 2025 images available</div>
              )}
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
                disabled={
                  (selectedImageIndex2024 === null &&
                    selectedImageIndex2025 === null) ||
                  saving
                }
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
                <strong>Navigation:</strong> Use arrow keys (← →) to navigate
                between farms. Press Enter to save your selections.
              </p>
              <p>
                <strong>Requirements:</strong> At least one image must be
                selected. When available, select one image from each year for
                comprehensive annotation.
              </p>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
