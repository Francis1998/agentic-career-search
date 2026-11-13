"""Skill extraction: alias normalization, symbol-aware boundaries and ambiguous words."""

from __future__ import annotations

import pytest

from autoapply_agent.services.skill_extraction import SKILLS, extract_skills, implied_skills


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("k8s, K8s and Kubernetes", ["kubernetes"]),
        ("Postgres, postgres and PostgreSQL 15", ["postgresql"]),
        ("JS and JavaScript (ES6)", ["javascript"]),
        ("ML, Machine-Learning and machine learning", ["machine learning"]),
        ("golang services", ["go"]),
        ("Node.js, NodeJS and node js", ["node.js"]),
        ("CI/CD, CICD and ci-cd", ["ci/cd"]),
        ("front-end, frontend and front end", ["frontend development"]),
        ("scikit-learn or sklearn", ["scikit-learn"]),
        ("Python3.11, C++17 and HTML5", ["python", "c++", "html"]),
        ("LLMs and microservices", ["large language models", "microservices"]),
        ("AWS (EC2, S3, EKS)", ["aws", "ec2", "amazon s3", "eks"]),
    ],
)
def test_aliases_fold_into_one_canonical_skill(text: str, expected: list[str]) -> None:
    assert extract_skills(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Go, Rust and Python", ["go", "rust", "python"]),
        ("Services written in Go.", ["go"]),
        ("good, going, Google, gopher, go-getter", []),
        ("Go above and beyond as the go-to person for Go-live support", []),
        ("go-to-market plans", ["go-to-market"]),
        ("C#, C++ and .NET", ["c#", "c++", ".net"]),
        ("C/C++", ["c", "c++"]),
        ("ASP.NET Core", ["asp.net"]),
        ("Objective-C", ["objective-c"]),
        ("JavaScript", ["javascript"]),
        ("NoSQL, MySQL and PL/SQL", ["nosql", "mysql", "pl/sql"]),
        ("Python, R, SQL", ["python", "r", "sql"]),
        ("statistics in R and SAS", ["statistics", "r", "sas"]),
        ("R&D, R & D, R. Smith, Mary R Smith, Acme(R), (C) 2026", []),
        ("Series C startup, C-suite, Grade C, Vitamin C, USB-C, plan c", []),
        ("Excel at communication", []),
        ("Advanced Excel and Spark", ["excel", "spark"]),
        ("the rest of the team; REST APIs", ["rest api"]),
        ("Spark joy", []),
        ("AI-powered startup", []),
        ("AI/ML", ["artificial intelligence", "machine learning"]),
        ("RAG pipelines; RAG status reports", ["retrieval-augmented generation"]),
        ("Ask us about accessibility accommodations; WCAG 2.2", ["accessibility"]),
    ],
)
def test_word_boundaries_and_ambiguous_words(text: str, expected: list[str]) -> None:
    assert extract_skills(text) == expected


def test_skills_are_distinct_in_order_of_first_mention() -> None:
    assert extract_skills("Kubernetes, Python, k8s, python3, Go") == ["kubernetes", "python", "go"]


def test_every_lexicon_alias_resolves_to_its_own_skill() -> None:
    for skill in SKILLS:
        for surface in (*skill.aliases, *skill.exact):
            assert extract_skills(f"Experience: {surface}.") == [skill.name], surface


def test_implied_skills_follow_chains_and_skip_named_skills() -> None:
    implied = implied_skills(["pytorch", "postgresql", "machine learning"])

    assert implied == {
        "artificial intelligence": ["machine learning", "pytorch"],
        "deep learning": ["pytorch"],
        "sql": ["postgresql"],
    }
