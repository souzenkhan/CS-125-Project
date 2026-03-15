//
//  HomeView.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import SwiftUI
import CoreLocation

struct HomeView: View {
    @State private var halal = false
    @State private var vegan = false
    @State private var vegetarian = false
    @State private var glutenFree = false
    @State private var transportMode = "Walk"

    @State private var queryText: String = ""
    @State private var maxDistance: Double = 1.0

    @State private var results: [Restaurant] = []
    @State private var isLoading = false

    @State private var showResults = false
    @State private var showErrorAlert = false
    @State private var errorMessage = ""

    // UCI campus center (approx)
    private let campusCenter = CLLocation(latitude: 33.6405, longitude: -117.8443)

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text("Search")) {
                    TextField("e.g., coffee, boba, shawarma", text: $queryText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
                .listRowBackground(Color.blue.opacity(0.1))

                Section(header: Text("Dietary Preferences")) {
                    Toggle("Halal", isOn: $halal).tint(.blue)
                    Toggle("Vegan", isOn: $vegan).tint(.blue)
                    Toggle("Vegetarian", isOn: $vegetarian).tint(.blue)
                    Toggle("Gluten Free", isOn: $glutenFree).tint(.blue)
                }
                .listRowBackground(Color.blue.opacity(0.1))

                Section(header: Text("Transportation")) {
                    Picker("Mode", selection: $transportMode) {
                        Text("Walk").tag("Walk")
                        Text("Drive").tag("Drive")
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: transportMode) { _, newMode in
                        if newMode == "Walk" {
                            maxDistance = 2
                        } else {
                            maxDistance = 8
                        }
                    }
                    

                    Text("Showing restaurants within \(Int(maxDistance)) miles")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }.listRowBackground(Color.blue.opacity(0.1))

                Section {
                    Button {
                        Task { await fetchRecommendations() }
                    } label: {
                        HStack {
                            if isLoading {
                                ProgressView()
                                    .padding(.trailing, 8)
                            }
                            Text(isLoading ? "Loading..." : "Get Recommendations")
                        }
                    }
                    .disabled(isLoading)
                }
                .listRowBackground(Color.blue.opacity(0.1))
            }
            .navigationTitle("Find Food")
            .toolbarBackground(Color.blue.opacity(0.15), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .navigationDestination(isPresented: $showResults) {
                ResultsView(restaurants: results, campusCenter: campusCenter)
            }
            .alert("API Error", isPresented: $showErrorAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage)
            }
            .scrollContentBackground(.hidden)
            .background(Color.blue.opacity(0.10))
        }
    }

    // MARK: - Networking

    func fetchRecommendations() async {
        isLoading = true
        defer { isLoading = false }

        do {
            // Build query: base text + soft dietary signals
            var q = queryText.trimmingCharacters(in: .whitespacesAndNewlines)

            // These aren't hard-filters on server yet; we add them to query to influence TF-IDF
            if vegan { q += " vegan" }
            if vegetarian { q += " vegetarian" }
            if glutenFree { q += " gluten free gluten_free" } // include both spellings

            q = q.trimmingCharacters(in: .whitespacesAndNewlines)
            if transportMode == "Walk" {
                maxDistance = 2
            } else {
                maxDistance = 8
            }

            let request = RecommendRequest(
                halal: halal,
                top_k: 20,      // ask for more, then filter locally by distance
                query: q.isEmpty ? nil : q
            )

            let serverResults = try await APIClient.shared.recommend(request: request)

            // Client-side distance filter (keeps server ranking order)
            let filtered = serverResults.filter { r in
                guard let lat = r.lat, let lng = r.lng else { return true } // keep if missing coords
                let loc = CLLocation(latitude: lat, longitude: lng)
                let miles = campusCenter.distance(from: loc) / 1609.344
                return miles <= maxDistance
            }

            // Optional client-side hard filter for toggles (if you want these to truly filter)
            let hardFiltered = filtered.filter { r in
                let tags = Set(r.dietary_tags)
                if vegan && !tags.contains("vegan") { return false }
                if vegetarian && !tags.contains("vegetarian") { return false }
                if glutenFree && !tags.contains("gluten_free") { return false }
                return true
            }

            results = Array(hardFiltered.prefix(10)) // show top 10 in app
            showResults = true

        } catch {
            errorMessage = error.localizedDescription
            showErrorAlert = true
        }
    }
}

#Preview {
    HomeView()
}