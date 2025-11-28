"""
Quick script to list all available farm IDs for assignment
Run this to get a list of farm IDs you can assign to users
"""
import os
import json

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FARM_DATASET_DIR = os.path.join(os.path.dirname(ROOT_DIR), "farm_dataset")

def list_all_farms():
    """List all available farm IDs"""
    if not os.path.isdir(FARM_DATASET_DIR):
        print(f"Error: Farm dataset directory not found: {FARM_DATASET_DIR}")
        return
    
    farm_dirs = [d for d in os.listdir(FARM_DATASET_DIR)
                 if os.path.isdir(os.path.join(FARM_DATASET_DIR, d)) and d != "0"]
    farm_dirs.sort()
    
    print(f"\n{'='*60}")
    print(f"Total Farms Available: {len(farm_dirs)}")
    print(f"{'='*60}\n")
    
    # Print in groups of 10 for easy copying
    for i in range(0, len(farm_dirs), 10):
        group = farm_dirs[i:i+10]
        print(f"Farm IDs {i+1}-{i+len(group)}:")
        print(", ".join(group))
        print()
    
    # Save to JSON for easy reference
    output_file = os.path.join(os.path.dirname(ROOT_DIR), "available_farms.json")
    with open(output_file, 'w') as f:
        json.dump({"farm_ids": farm_dirs, "total": len(farm_dirs)}, f, indent=2)
    
    print(f"✓ Farm IDs saved to: {output_file}")
    print(f"\nTo assign farms to a user, copy and paste the IDs (comma-separated)")
    print(f"Example: {', '.join(farm_dirs[:5])}")

if __name__ == "__main__":
    list_all_farms()
