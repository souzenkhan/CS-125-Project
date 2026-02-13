//
//  ResultsView.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import SwiftUI
import CoreLocation

struct ResultsView: View {
    let restaurants: [Restaurant]
    let campusCenter: CLLocation

    var body: some View {
        List(restaurants) { restaurant in
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(restaurant.name)
                        .font(.headline)

                    Spacer()

                    if let score = restaurant.score {
                        Text(String(format: "%.3f", score))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                HStack(spacing: 12) {
                    Text(String(format: "⭐️ %.1f", restaurant.rating))
                        .font(.subheadline)

                    if let miles = distanceMiles(for: restaurant) {
                        Text(String(format: "%.1f mi", miles))
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }

                if !restaurant.dietary_tags.isEmpty {
                    Text(restaurant.dietary_tags.joined(separator: " • "))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                if !restaurant.why.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(restaurant.why, id: \.self) { bullet in
                            HStack(alignment: .top, spacing: 6) {
                                Text("•")
                                Text(bullet)
                            }
                            .font(.caption)
                            .foregroundColor(.gray)
                        }
                    }
                }
            }
            .padding(.vertical, 6)
        }
        .navigationTitle("Results")
    }

    private func distanceMiles(for r: Restaurant) -> Double? {
        guard let lat = r.lat, let lng = r.lng else { return nil }
        let loc = CLLocation(latitude: lat, longitude: lng)
        return campusCenter.distance(from: loc) / 1609.344
    }
}