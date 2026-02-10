import Foundation

class APIClient {
    static let shared = APIClient()

    private let baseURL = "http://127.0.0.1:8000"

    func recommend(request: RecommendRequest) async throws -> [Restaurant] {
        guard let url = URL(string: "\(baseURL)/recommend") else {
            throw URLError(.badURL)
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder().encode(request)

        let (data, response) = try await URLSession.shared.data(for: urlRequest)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        return try JSONDecoder().decode([Restaurant].self, from: data)
    }
}
