//
//  ResultsView.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import SwiftUI


struct ResultsView: View {
    let restaurants: [Restaurant]

    var body: some View {
        List(restaurants) { restaurant in
            VStack(alignment: .leading, spacing: 6) {
                Text(restaurant.name)
                    .font(.headline)

                Text(String(format: "Rating: %.1f", restaurant.rating))
                    .font(.subheadline)

                if !restaurant.why.isEmpty {
                    Text(restaurant.why.joined(separator: ", "))
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }
        }
        .navigationTitle("Results")
    }
}
