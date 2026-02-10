//
//  HomeView.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import SwiftUI

struct HomeView: View {
    @State private var halal = false
    @State private var vegan = false
    @State private var vegetarian = false
    @State private var glutenFree = false
    @State private var results: [Restaurant] = []
    @State private var isLoading = false
    
    @State private var maxDistance: Double = 1.0
    @State private var showResults = false
    
    var body: some View {
        NavigationStack {
            Form{
                Section(header: Text("Dietary Preferences")){
                    Toggle("Halal", isOn: $halal)
                    Toggle("Vegan", isOn: $vegan)
                    Toggle("Vegetarian", isOn: $vegetarian)
                    Toggle("Gluten Free", isOn: $glutenFree)
                }
                Section(header: Text("Max Distance")) {
                    Slider(value: $maxDistance, in: 0.5...5.0, step: 0.5)
                    Text("\(maxDistance, specifier: "%.1f") miles")
                }
                Section {
                    Button("Get Recommendations") {
                        Task {
                            await fetchRecommendations()
                        }
                    }
                }
            }
            .navigationTitle("Find Food")
            .navigationDestination(isPresented: $showResults) {
                ResultsView(restaurants: results)
            }
        }
    }

    func fetchRecommendations() async {
        print("FETCH CALLED")
        isLoading = true
        do {
            let request = RecommendRequest(halal: halal, top_k: 5)

            results = try await APIClient.shared.recommend(request: request)
            showResults = true
        } catch {
            print("API error:", error)
        }
        isLoading = false
    }
}

#Preview {
    HomeView()
}
