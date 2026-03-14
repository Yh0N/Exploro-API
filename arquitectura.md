exploro-api/
│
├── app/
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── database/
│   │   └── connection.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── profile.py
│   │   ├── place.py
│   │   ├── review.py
│   │   ├── recommendation.py
│   │   └── pyme.py
│   │
│   ├── schemas/
│   │   ├── user_schema.py
│   │   ├── place_schema.py
│   │   └── review_schema.py
│   │
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   ├── place_routes.py
│   │   ├── review_routes.py
│   │   └── recommendation_routes.py
│   │
│   └── services/
│       ├── auth_service.py
│       ├── place_service.py
│       ├── review_service.py
│       ├── recommendation_service.py
│       ├── collaborative_filter.py
│       ├── linear_regression.py
│       └── sentiment_analysis.py
│
├── tests/
│
├── .env
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── main.py