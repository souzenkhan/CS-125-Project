//
//  ResultsView.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import SwiftUI

import SwiftUI

struct ResultsView: View {
    let restaurants: [Restaurant]

    var body: some View {
        List(restaurants) { restaurant in
            VStack(alignment: .leading, spacing: 6) {
                Text(restaurant.name)
                    .font(.headline)

                Text(restaurant.dietaryTags.joined(separator: ", "))
                    .font(.subheadline)
                    .foregroundColor(.gray)

                HStack {
                    Text("⭐️ \(restaurant.rating, specifier: "%.1f")")
                    Spacer()
                    Text("\(restaurant.distanceMiles, specifier: "%.1f") mi")
                }
                .font(.caption)
            }
            .padding(.vertical, 6)
        }
        .navigationTitle("Results")
    }
}
