import math
import time
import random

# Original implementation
def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def cluster_items_orig(items, max_dist):
    if not items:
        return []
    
    clusters = []
    for item in items:
        if item.get("shape_type") == "rect":
            x, y, w, h = item["x"], item["y"], item["width"], item["height"]
            points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
        else:
            points = item.get("points", [item["start"], item["end"]])
            
        matched_clusters = []
        for i, cluster in enumerate(clusters):
            is_close = False
            for p1 in points:
                for c_item in cluster:
                    if c_item.get("shape_type") == "rect":
                        cx, cy, cw, ch = c_item["x"], c_item["y"], c_item["width"], c_item["height"]
                        c_points = [(cx, cy), (cx+cw, cy), (cx+cw, cy+ch), (cx, cy+ch)]
                    else:
                        c_points = c_item.get("points", [c_item["start"], c_item["end"]])
                    for p2 in c_points:
                        if dist(p1, p2) <= max_dist:
                            is_close = True
                            break
                    if is_close:
                        break
                if is_close:
                    break
            if is_close:
                matched_clusters.append(i)
        
        if not matched_clusters:
            clusters.append([item])
        elif len(matched_clusters) == 1:
            clusters[matched_clusters[0]].append(item)
        else:
            new_cluster = [item]
            for i in sorted(matched_clusters, reverse=True):
                new_cluster.extend(clusters.pop(i))
            clusters.append(new_cluster)
    return clusters

# Optimized implementation
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import detect_patterns

def cluster_items_opt(items, max_dist):
    return detect_patterns.cluster_items(items, max_dist)
# Test and verify
def generate_random_items(num_items):
    items = []
    for i in range(num_items):
        if random.random() < 0.2:
            items.append({
                "shape_type": "rect",
                "x": random.uniform(0, 5000),
                "y": random.uniform(0, 5000),
                "width": random.uniform(5, 50),
                "height": random.uniform(5, 50)
            })
        else:
            items.append({
                "shape_type": "line",
                "start": (random.uniform(0, 5000), random.uniform(0, 5000)),
                "end": (random.uniform(0, 5000), random.uniform(0, 5000))
            })
    return items

# Generate test data
random.seed(42)
test_items = generate_random_items(3000)
max_dist = 20.0

print("Running original cluster_items...")
t0 = time.time()
clusters_orig = cluster_items_orig(test_items, max_dist)
t1 = time.time()
print(f"Original took {t1 - t0:.4f}s. Generated {len(clusters_orig)} clusters.")

print("Running optimized cluster_items...")
t2 = time.time()
clusters_opt = cluster_items_opt(test_items, max_dist)
t3 = time.time()
print(f"Optimized took {t3 - t2:.4f}s. Generated {len(clusters_opt)} clusters.")

# Compare results
# Since order inside cluster might be different, let's normalize clusters by sorting them.
def normalize_clusters(clusters):
    norm_c = []
    for c in clusters:
        # Sort items inside cluster by their representation
        sorted_c = sorted(c, key=lambda x: str(x))
        norm_c.append(sorted_c)
    # Sort clusters by their first element's representation
    return sorted(norm_c, key=lambda x: str(x[0]))

norm_orig = normalize_clusters(clusters_orig)
norm_opt = normalize_clusters(clusters_opt)

if len(norm_orig) != len(norm_opt):
    print(f"MISMATCH: Lengths differ: {len(norm_orig)} vs {len(norm_opt)}")
else:
    mismatch = False
    for idx, (c1, c2) in enumerate(zip(norm_orig, norm_opt)):
        if len(c1) != len(c2):
            print(f"MISMATCH at cluster {idx}: lengths differ {len(c1)} vs {len(c2)}")
            mismatch = True
            break
        for item1, item2 in zip(c1, c2):
            if item1 != item2:
                print(f"MISMATCH in cluster {idx}: {item1} vs {item2}")
                mismatch = True
                break
        if mismatch:
            break
    if not mismatch:
        print("SUCCESS: Both implementations produced identical clusters!")
