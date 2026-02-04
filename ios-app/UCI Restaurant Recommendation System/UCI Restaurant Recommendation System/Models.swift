//
//  Models.swift
//  UCI Restaurant Recommendation System
//
//  Created by Souzen Khan on 2/4/26.
//

import Foundation

struct Restaurant: Identifiable {
    let id: String
    let name: String
    let dietaryTags: [String]
    let rating: Double
    let distanceMiles: Double
}
