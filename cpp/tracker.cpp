#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <vector>

extern "C" {
struct EVDetection { double x, y, w, h; };
struct EVTrack { int id; double x, y, w, h; int missed; };
}

namespace {
struct Track { int id; EVDetection box; int missed; };
class Tracker {
public:
    explicit Tracker(double max_distance, int max_missed)
        : max_distance_(max_distance), max_missed_(max_missed) {}
    int update(const EVDetection* detections, int count, EVTrack* output, int capacity) {
        if (count < 0 || capacity < 0 || (count && !detections) || (capacity && !output)) return -1;
        for (int i = 0; i < count; ++i) {
            const auto& d = detections[i];
            if (!std::isfinite(d.x) || !std::isfinite(d.y) || !std::isfinite(d.w) || !std::isfinite(d.h)
                || d.w <= 0 || d.h <= 0) return -2;
        }
        // Deterministic global-greedy nearest-centroid matching. Not optimal for crossings.
        struct Candidate { double distance; size_t t; int d; };
        std::vector<Candidate> candidates;
        for (size_t t = 0; t < tracks_.size(); ++t) {
            for (int d = 0; d < count; ++d) {
                auto a = tracks_[t].box, b = detections[d];
                double dist = std::hypot((a.x + a.w / 2) - (b.x + b.w / 2),
                                         (a.y + a.h / 2) - (b.y + b.h / 2));
                if (dist <= max_distance_) candidates.push_back({dist, t, d});
            }
        }
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
            if (a.distance != b.distance) return a.distance < b.distance;
            if (a.t != b.t) return a.t < b.t;
            return a.d < b.d;
        });
        std::vector<bool> matched_t(tracks_.size(), false), matched_d(count, false);
        for (const auto& c : candidates) {
            if (matched_t[c.t] || matched_d[c.d]) continue;
            matched_t[c.t] = true;
            matched_d[c.d] = true;
            tracks_[c.t].box = detections[c.d];
            tracks_[c.t].missed = 0;
        }
        for (size_t i = 0; i < matched_t.size(); ++i) {
            if (!matched_t[i]) ++tracks_[i].missed;
        }
        tracks_.erase(std::remove_if(tracks_.begin(), tracks_.end(), [this](const Track& t) {
            return t.missed > max_missed_;
        }), tracks_.end());
        for (int d = 0; d < count; ++d) {
            if (!matched_d[d]) tracks_.push_back({next_id_++, detections[d], 0});
        }
        const int n = static_cast<int>(tracks_.size());
        if (capacity < n) return -3;
        for (int i = 0; i < n; ++i) {
            const auto& t = tracks_[i];
            output[i] = {t.id, t.box.x, t.box.y, t.box.w, t.box.h, t.missed};
        }
        return n;
    }
private:
    double max_distance_;
    int max_missed_;
    int next_id_ = 1;
    std::vector<Track> tracks_;
};
}

extern "C" {
void* ev_tracker_create(double max_distance, int max_missed) {
    if (!std::isfinite(max_distance) || max_distance <= 0 || max_missed < 0) return nullptr;
    try { return new Tracker(max_distance, max_missed); } catch (...) { return nullptr; }
}
void ev_tracker_destroy(void* tracker) { delete static_cast<Tracker*>(tracker); }
int ev_tracker_update(void* tracker, const EVDetection* detections, int count,
                      EVTrack* output, int capacity) {
    if (!tracker) return -1;
    try { return static_cast<Tracker*>(tracker)->update(detections, count, output, capacity); }
    catch (...) { return -4; }
}
}
