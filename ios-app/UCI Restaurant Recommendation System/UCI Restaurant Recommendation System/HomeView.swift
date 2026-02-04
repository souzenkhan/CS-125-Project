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
    
    @State private var maxDistance: Double = 1.0
    @State private var showResults = false
    
    let dummyRestaurants: [Restaurant] = [
        Restaurant(id: "moongoat_coffee",
                   name: "MoonGoat Coffee",
                   dietaryTags: ["vegan", "vegetarian"],
                   rating: 4.4,
                   distanceMiles: 0.4),
        Restaurant(id: "halal_shack",
                   name: "Halal Shack",
                   dietaryTags: ["halal", "vegetarian"],
                   rating: 3.5,
                   distanceMiles: 0.1),
        Restaurant(id: "chipotle",
                   name: "Chipotle",
                   dietaryTags: ["vegetarian"],
                   rating: 4.0,
                   distanceMiles: 1.1),
    ]
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
                        showResults = true
                    }
                }
            }
            .navigationTitle("Find Food")
            .navigationDestination(isPresented: $showResults) {
                ResultsView(restaurants: dummyRestaurants)
            }
        }
    }
}

#Preview {
    HomeView()
}
