//
//  Models.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import Foundation

struct Restaurant: Identifiable, Codable {
    let id: String
    let name: String
    let dietary_tags: [String]
    let rating: Double
    let review_count: Int?
    let score: Double
    let why: [String]
}

struct RecommendRequest: Codable {
    let halal: Bool
    let top_k: Int
}

struct RecommendResponse: Codable {
    let results: [Restaurant]
}