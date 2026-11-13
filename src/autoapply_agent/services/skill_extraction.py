"""Deterministic skill extraction with a curated, alias-aware lexicon.

Resume-to-job matching (:mod:`autoapply_agent.services.resume_match`) runs this on both
sides: free-form resume text and each captured job's title and description. Every alias
of a skill folds to one canonical name (``k8s`` → ``kubernetes``, ``Postgres`` →
``postgresql``, ``JS`` → ``javascript``, ``ML`` → ``machine learning``), so a resume and a
posting that spell a skill differently still match. No network access and no LLM.

Matching rules:

* one compiled regular expression scans the text, longest alias first, so
  ``React Native`` is one skill and ``ASP.NET`` does not also count as ``.NET``;
* aliases match case-insensitively at boundaries that understand symbols: ``C++``,
  ``C#``, ``.NET``, ``Node.js`` and ``CI/CD`` are whole skills, ``Java`` never matches
  inside ``JavaScript`` and ``SQL`` never inside ``NoSQL`` or ``MySQL``;
* a space or hyphen inside an alias accepts any run of spaces, hyphens or underscores,
  or none (``front-end`` = ``frontend`` = ``front end``);
* an attached version number or a plural ``s`` is allowed (``Python3``, ``C++17``,
  ``HTML5``, ``LLMs``);
* ambiguous short words are *exact* aliases: case-sensitive (``Go``, ``R``, ``C``, ``AI``,
  ``ML``, ``Excel``, ``Spark`` …), never touching ``-``, ``&`` or an apostrophe, and
  rejected in known non-skill contexts (``Go above and beyond``, ``R&D``, ``R. Smith``,
  ``Series C``, ``Vitamin C``, ``(C)``).

``implies`` records skills that a resume skill demonstrates (``postgresql`` → ``sql``,
``eks`` → ``kubernetes`` and ``aws``); matching applies the transitive closure to the
resume side only, so a posting never gains requirements it did not state.
"""

from __future__ import annotations

import re
import string
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

__all__ = [
    "SKILLS",
    "SKILLS_BY_NAME",
    "Skill",
    "extract_skills",
    "implied_skills",
]


@dataclass(frozen=True, slots=True)
class Skill:
    """One canonical skill of the lexicon.

    Attributes:
        name: Canonical lowercase name reported in match results.
        aliases: Case-insensitive surface forms (see the module docstring).
        exact: Case-sensitive surface forms for ambiguous short words.
        implies: Canonical names of skills this one demonstrates.
    """

    name: str
    aliases: tuple[str, ...] = ()
    exact: tuple[str, ...] = ()
    implies: tuple[str, ...] = ()


def _skill(
    name: str,
    *aliases: str,
    exact: tuple[str, ...] = (),
    implies: tuple[str, ...] = (),
    name_is_alias: bool = True,
) -> Skill:
    """Build a lexicon entry; the name is an alias unless an exact form spells it."""

    spelled_exactly = name.casefold() in {form.casefold() for form in exact}
    surface = (name, *aliases) if name_is_alias and not spelled_exactly else aliases
    return Skill(name=name, aliases=tuple(surface), exact=exact, implies=implies)


SKILLS: tuple[Skill, ...] = (
    # Programming languages
    _skill("python"),
    _skill("java"),
    _skill("javascript", "js", "ecmascript", "es6"),
    _skill("typescript", implies=("javascript",)),
    _skill("go", "golang", exact=("Go",)),
    _skill("rust"),
    _skill("c", exact=("C",)),
    _skill("c++", "cpp"),
    _skill("c#", "c sharp"),
    _skill("ruby"),
    _skill("php"),
    _skill("scala"),
    _skill("kotlin"),
    _skill("swift", exact=("Swift",)),
    _skill("objective-c", "objc"),
    _skill("r", "r programming", "rstudio", exact=("R",)),
    _skill("sql"),
    _skill("bash", "shell scripting", "shell script"),
    _skill("powershell"),
    _skill("perl"),
    _skill("haskell"),
    _skill("elixir"),
    _skill("erlang"),
    _skill("clojure"),
    _skill("lua"),
    _skill("dart", exact=("Dart",)),
    _skill("matlab"),
    _skill("fortran"),
    _skill("cobol"),
    _skill("groovy"),
    _skill("f#"),
    _skill("solidity"),
    _skill("sas", exact=("SAS",)),
    _skill("vba"),
    # Web and frontend
    _skill("html"),
    _skill("css"),
    _skill("sass", "scss"),
    _skill("tailwind css", "tailwind", "tailwindcss"),
    _skill("react", "react.js", "reactjs", implies=("javascript",)),
    _skill("react native", implies=("react", "mobile development")),
    _skill("vue", "vue.js", "vuejs", implies=("javascript",)),
    _skill("angular", "angularjs", "angular.js", implies=("javascript",)),
    _skill("svelte", "sveltekit", implies=("javascript",)),
    _skill("next.js", "nextjs", implies=("react",)),
    _skill("node.js", "node js", implies=("javascript",)),
    _skill("express.js", "express js", implies=("node.js",)),
    _skill("nestjs", "nest.js", implies=("node.js",)),
    _skill("jquery", implies=("javascript",)),
    _skill("redux", implies=("javascript",)),
    _skill("webpack"),
    _skill("graphql"),
    _skill("frontend development", "front end"),
    _skill("backend development", "back end"),
    _skill("full-stack development", "full stack"),
    _skill("web development", "web developer"),
    # Bare "accessibility" is left out: hiring boilerplate offers "accessibility
    # accommodations" in almost every posting.
    _skill("accessibility", "web accessibility", "wcag", "a11y", name_is_alias=False),
    _skill("ux design", "ux", "ui/ux", "ux/ui", "user experience", "user experience design"),
    _skill("ui design", "user interface design"),
    _skill("ux research", "user research", "usability testing"),
    _skill("figma"),
    # Backend frameworks, APIs and architecture
    _skill("django", implies=("python",)),
    _skill("flask", exact=("Flask",), implies=("python",)),
    _skill("fastapi", implies=("python",)),
    _skill(
        "spring",
        "spring boot",
        "spring framework",
        "spring mvc",
        "spring cloud",
        implies=("java",),
        name_is_alias=False,
    ),
    _skill("ruby on rails", exact=("Rails",), implies=("ruby",)),
    _skill("laravel", implies=("php",)),
    _skill("symfony", implies=("php",)),
    _skill(".net", ".net core", "dotnet", "vb.net"),
    _skill("asp.net", "asp.net core", "asp.net mvc", implies=(".net",)),
    _skill("grpc"),
    _skill("rest api", "restful", "restful api", exact=("REST",)),
    _skill("api design", "api development"),
    _skill("microservices", "microservice"),
    _skill("distributed systems", "distributed system"),
    _skill("system design", "systems design"),
    _skill("event-driven architecture", "event driven"),
    _skill("object-oriented programming", "object oriented", "oop"),
    _skill("functional programming"),
    _skill("design patterns"),
    _skill("embedded systems", "embedded software", "firmware"),
    # Data, analytics and machine learning
    _skill("artificial intelligence", exact=("AI",)),
    _skill("machine learning", exact=("ML",), implies=("artificial intelligence",)),
    _skill("deep learning", implies=("machine learning",)),
    _skill("natural language processing", "nlp"),
    _skill("computer vision"),
    _skill("reinforcement learning", implies=("machine learning",)),
    _skill("large language models", "large language model", "llm"),
    _skill("generative ai", "gen ai", implies=("artificial intelligence",)),
    _skill("prompt engineering"),
    _skill("retrieval-augmented generation", exact=("RAG",)),
    _skill("langchain"),
    _skill("llamaindex", "llama index"),
    _skill("hugging face"),
    _skill("pytorch", implies=("deep learning",)),
    _skill("tensorflow", implies=("deep learning",)),
    _skill("keras", implies=("deep learning",)),
    _skill("scikit-learn", "sklearn", implies=("machine learning", "python")),
    _skill("xgboost", implies=("machine learning",)),
    _skill("lightgbm", implies=("machine learning",)),
    _skill("pandas", implies=("python",)),
    _skill("numpy", implies=("python",)),
    _skill("scipy", implies=("python",)),
    _skill("jupyter", "jupyter notebook", "jupyterlab"),
    _skill("mlops", implies=("machine learning",)),
    _skill("mlflow", implies=("mlops",)),
    _skill("kubeflow", implies=("mlops", "kubernetes")),
    _skill("sagemaker", "amazon sagemaker", "aws sagemaker", implies=("aws", "machine learning")),
    _skill("vertex ai", implies=("gcp", "machine learning")),
    _skill("opencv", implies=("computer vision",)),
    _skill("spacy", implies=("natural language processing",)),
    _skill("nltk", implies=("natural language processing",)),
    _skill("data science", "data scientist"),
    _skill("data analysis", "data analytics", "data analyst"),
    _skill("data engineering", "data engineer", "data pipeline"),
    _skill("data visualization", "data visualisation", "data viz"),
    _skill("statistics", "statistical analysis", "statistical modeling", "statistical modelling"),
    _skill("a/b testing", "a/b test", "ab test", "split testing"),
    _skill("etl", "elt"),
    _skill("data modeling", "data modelling"),
    _skill("data warehousing", "data warehouse"),
    _skill(
        "recommendation systems",
        "recommendation system",
        "recommender system",
        "recommender systems",
    ),
    _skill("feature engineering"),
    _skill("spark", "apache spark", exact=("Spark",)),
    _skill("pyspark", implies=("spark", "python")),
    _skill("hadoop", "apache hadoop"),
    _skill("hive", "apache hive", "hiveql", exact=("Hive",)),
    _skill("kafka", "apache kafka"),
    _skill("flink", "apache flink"),
    _skill("airflow", "apache airflow", exact=("Airflow",)),
    _skill("dbt"),
    _skill("databricks", implies=("spark",)),
    _skill("snowflake", implies=("sql",)),
    _skill("bigquery", "big query", implies=("gcp", "sql")),
    _skill("redshift", "amazon redshift", implies=("aws", "sql")),
    _skill("kinesis", "amazon kinesis", implies=("aws",)),
    _skill("tableau", implies=("data visualization",)),
    _skill("power bi", implies=("data visualization",)),
    _skill("looker", implies=("data visualization",)),
    _skill("excel", "ms excel", "microsoft excel", exact=("Excel",)),
    _skill("google analytics"),
    _skill("mixpanel"),
    # Cloud, infrastructure and operations
    _skill("aws", "amazon web services"),
    _skill("gcp", "google cloud", "google cloud platform"),
    _skill("azure", "microsoft azure"),
    _skill("ec2", "amazon ec2", "aws ec2", implies=("aws",)),
    _skill("amazon s3", "aws s3", exact=("S3",), implies=("aws",)),
    _skill("aws lambda", implies=("aws", "serverless")),
    _skill("dynamodb", implies=("aws", "nosql")),
    _skill(
        "cloudformation",
        "aws cloudformation",
        implies=("aws", "infrastructure as code"),
    ),
    _skill("eks", "amazon eks", implies=("aws", "kubernetes")),
    _skill("ecs", "amazon ecs", implies=("aws",)),
    _skill("gke", "google kubernetes engine", implies=("gcp", "kubernetes")),
    _skill("aks", "azure kubernetes service", implies=("azure", "kubernetes")),
    _skill("serverless"),
    _skill("docker"),
    _skill("kubernetes", "k8s"),
    _skill("helm", "helm chart", exact=("Helm",), implies=("kubernetes",)),
    _skill("openshift", implies=("kubernetes",)),
    _skill("terraform", implies=("infrastructure as code",)),
    _skill("pulumi", implies=("infrastructure as code",)),
    _skill("ansible", implies=("infrastructure as code",)),
    _skill("infrastructure as code", "iac"),
    _skill("argo cd", implies=("kubernetes", "ci/cd")),
    _skill("jenkins", implies=("ci/cd",)),
    _skill("github actions", implies=("ci/cd",)),
    _skill("gitlab ci", "gitlab ci/cd", implies=("ci/cd",)),
    _skill("circleci", "circle ci", implies=("ci/cd",)),
    _skill(
        "ci/cd",
        "ci cd",
        "continuous integration",
        "continuous delivery",
        "continuous deployment",
    ),
    _skill("devops", "dev ops"),
    _skill("site reliability engineering", "site reliability", "sre"),
    _skill("platform engineering", "platform engineer"),
    _skill("observability"),
    _skill("prometheus"),
    _skill("grafana"),
    _skill("datadog"),
    _skill("splunk"),
    _skill("new relic"),
    _skill("opentelemetry", "open telemetry"),
    _skill("elasticsearch", "elastic search", "elk", "elk stack"),
    _skill("incident response", "incident management"),
    _skill("linux"),
    _skill("unix"),
    _skill("git"),
    _skill("nginx"),
    # Databases and messaging
    _skill("postgresql", "postgres", implies=("sql",)),
    _skill("mysql", implies=("sql",)),
    _skill(
        "sql server",
        "mssql",
        "ms sql",
        "microsoft sql server",
        "t-sql",
        implies=("sql",),
    ),
    _skill("sqlite", implies=("sql",)),
    _skill("mariadb", implies=("sql",)),
    _skill("oracle database", "oracle db", implies=("sql",)),
    _skill("pl/sql", implies=("sql", "oracle database")),
    _skill("nosql"),
    _skill("mongodb", "mongo", implies=("nosql",)),
    _skill("cassandra", "apache cassandra", exact=("Cassandra",), implies=("nosql",)),
    _skill("redis"),
    _skill("memcached"),
    _skill("neo4j"),
    _skill("rabbitmq"),
    _skill("amazon sqs", "aws sqs", "sqs", implies=("aws",)),
    # Testing and quality
    _skill("unit testing", "unit test"),
    _skill("integration testing", "integration test"),
    _skill("test automation", "automated testing", "automation testing"),
    _skill("test-driven development", "tdd", "test driven"),
    _skill("quality assurance", exact=("QA",)),
    _skill("pytest", implies=("python",)),
    _skill("junit", implies=("java",)),
    _skill("jest", implies=("javascript",)),
    _skill("selenium"),
    _skill("cypress", exact=("Cypress",)),
    _skill("playwright"),
    # Security
    _skill("cybersecurity", "cyber security", "information security", "infosec"),
    _skill("application security", "appsec"),
    _skill(
        "penetration testing",
        "penetration test",
        "pen testing",
        "pen test",
        "pentesting",
    ),
    _skill("identity and access management", exact=("IAM",)),
    _skill("oauth", "openid connect", "oidc"),
    _skill("soc 2"),
    # Mobile
    _skill("mobile development", "mobile app development", "mobile engineering"),
    _skill("ios", implies=("mobile development",)),
    _skill("android", implies=("mobile development",)),
    _skill("swiftui", implies=("swift", "ios")),
    _skill("flutter", implies=("dart", "mobile development")),
    # Delivery practices and collaboration tools
    _skill("agile"),
    _skill("scrum", implies=("agile",)),
    _skill("kanban", implies=("agile",)),
    _skill("jira"),
    _skill("confluence"),
    # Business, product and go-to-market
    _skill("product management", "product manager", "product owner"),
    _skill("project management", "project manager", exact=("PMP",)),
    _skill("program management", "program manager"),
    _skill("stakeholder management"),
    _skill("go-to-market"),
    _skill("sales", "b2b sales", "enterprise sales", "saas sales", name_is_alias=False),
    _skill("account management", "account manager"),
    _skill("business development"),
    _skill("customer success"),
    _skill("payments", "payment processing", "payment systems"),
    _skill("digital marketing"),
    _skill("content marketing"),
    _skill("email marketing"),
    _skill("seo", "search engine optimization"),
    _skill("google ads"),
    _skill("salesforce"),
    _skill("hubspot"),
    _skill("sap", exact=("SAP",)),
    _skill("netsuite"),
    _skill("quickbooks"),
    _skill("financial modeling", "financial modelling", "financial model"),
    _skill("financial analysis"),
    _skill("forecasting"),
    _skill("budgeting", "budget management"),
    _skill("accounting"),
    _skill("gaap", exact=("GAAP",)),
    _skill("technical writing"),
    _skill("six sigma", "lean six sigma"),
)
"""The curated lexicon (canonical names are unique and lowercase)."""

SKILLS_BY_NAME: Mapping[str, Skill] = {skill.name: skill for skill in SKILLS}

# Besides letters, digits and "_", these make a position part of the token on its left.
_LEFT_JOINERS = frozenset(".+#")
# Lowercases ASCII only, so match offsets in the lowered text equal those in the original.
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
# Exact aliases never touch these (``Go-to``, ``R&D``, ``AI's``, ``USB-C``).
_EXACT_BLOCKERS = frozenset("-&'\u2019@$")
_SEPARATORS = re.compile(r"[\s_-]+")
_VERSION_SUFFIX = re.compile(r"\d+(?:\.\d+)*$")
_PREVIOUS_WORD = re.compile(r"([A-Za-z]+)[ \t]+$")
_NEXT_WORD = re.compile(r"[ \t]+([A-Za-z]+)")
_INITIAL = re.compile(r"\.[ \t]*[A-Z]")
_AMPERSAND = re.compile(r"[ \t]*&")
# Words that turn a single capital letter into a label: ``Series C``, ``Plan B``...
_LETTER_LABELS = frozenset(
    {
        "appendix",
        "area",
        "block",
        "building",
        "category",
        "class",
        "exhibit",
        "figure",
        "floor",
        "form",
        "gate",
        "grade",
        "group",
        "hepatitis",
        "level",
        "lot",
        "option",
        "part",
        "phase",
        "plan",
        "rating",
        "room",
        "round",
        "route",
        "schedule",
        "section",
        "series",
        "size",
        "stage",
        "step",
        "suite",
        "table",
        "team",
        "tier",
        "type",
        "unit",
        "version",
        "vitamin",
        "wing",
        "zone",
    }
)
# Exact alias -> words that, right after it, show a non-skill meaning.
_REJECT_NEXT: Mapping[str, frozenset[str]] = {
    "Go": frozenset(
        {
            "above",
            "ahead",
            "along",
            "back",
            "beyond",
            "big",
            "deep",
            "far",
            "forward",
            "get",
            "home",
            "live",
            "out",
            "over",
            "the",
            "through",
        }
    ),
    "Excel": frozenset({"at", "in", "within"}),
    "Spark": frozenset(
        {"change", "creativity", "curiosity", "ideas", "innovation", "interest", "joy"}
    ),
    "Swift": frozenset({"action", "decisions", "delivery", "execution", "response"}),
    # Red/amber/green project reporting.
    "RAG": frozenset({"rating", "ratings", "report", "reporting", "status"}),
}
# Exact alias -> words that, right before it, show a non-skill meaning.
_REJECT_PREVIOUS: Mapping[str, frozenset[str]] = {
    "Helm": frozenset({"the"}),
    "Rails": frozenset({"guard", "safety"}),
}
# Exact aliases that are also given names: rejected before a capitalized surname.
_NAME_LIKE = frozenset({"Cassandra"})


def _fold(text: str) -> str:
    """Case-fold and drop separators, the key every alias spelling shares."""

    return _SEPARATORS.sub("", text.casefold())


def _alias_regex(alias: str) -> str:
    """Regex for one alias: spaces and hyphens become optional separator runs."""

    parts = [part for part in re.split(r"[ -]+", alias) if part]
    return r"[\s_-]*".join(re.escape(part) for part in parts)


def _scanner_regex(aliases: Iterable[str]) -> str:
    """One alternation of lowercase aliases, grouped by first character, longest first.

    Grouping lets the regex engine reject most alternatives with a single character
    comparison; longest-first order makes a longer alias win over its own prefix at
    the same position (``react native`` before ``react``).
    """

    groups: dict[str, list[str]] = {}
    for alias in sorted(set(aliases), key=lambda item: (-len(_fold(item)), item)):
        head = re.escape(alias[0])
        groups.setdefault(head, []).append(_alias_regex(alias)[len(head) :])
    branches = (head + "(?:" + "|".join(tails) + ")" for head, tails in sorted(groups.items()))
    return "(?:" + "|".join(branches) + ")"


def _build_indexes() -> tuple[dict[str, str], dict[str, str], re.Pattern[str]]:
    """Index aliases by folded spelling and exact form; compile the scanner.

    Raises:
        ValueError: If two skills claim the same alias or an ``implies`` target is unknown.
    """

    folded: dict[str, str] = {}
    exact: dict[str, str] = {}
    for skill in SKILLS:
        if skill.name != skill.name.lower() or SKILLS_BY_NAME[skill.name] is not skill:
            raise ValueError(f"skill names must be unique and lowercase: {skill.name!r}")
        for alias in skill.aliases:
            key = _fold(alias)
            if folded.setdefault(key, skill.name) != skill.name:
                raise ValueError(f"alias {alias!r} is claimed by {folded[key]!r} too")
        for form in skill.exact:
            if exact.setdefault(form, skill.name) != skill.name:
                raise ValueError(f"exact alias {form!r} is claimed by {exact[form]!r} too")
        for target in skill.implies:
            if target not in SKILLS_BY_NAME:
                raise ValueError(f"{skill.name!r} implies unknown skill {target!r}")
    for form in exact:
        if _fold(form) in folded:
            raise ValueError(f"exact alias {form!r} also matches case-insensitively")
    aliases = [alias.lower() for skill in SKILLS for alias in (*skill.aliases, *skill.exact)]
    # The scanner runs on ASCII-lowercased text without re.IGNORECASE: case-insensitive
    # literals would defeat the engine's first-character checks. Exact aliases are
    # matched here regardless of case and checked against the original text afterwards.
    scanner = re.compile(_scanner_regex(aliases) + r"(?:s|\d+(?:\.\d+)*)?(?![\w+#]|\.\w)")
    return folded, exact, scanner


def _implication_closure() -> dict[str, frozenset[str]]:
    """Every skill each skill demonstrates, directly or transitively."""

    closure: dict[str, frozenset[str]] = {}
    for skill in SKILLS:
        seen: set[str] = set()
        pending = list(skill.implies)
        while pending:
            target = pending.pop()
            if target != skill.name and target not in seen:
                seen.add(target)
                pending.extend(SKILLS_BY_NAME[target].implies)
        closure[skill.name] = frozenset(seen)
    return closure


_FOLDED, _EXACT, _SCANNER = _build_indexes()
_IMPLIES = _implication_closure()


def _word_before(text: str, start: int) -> str | None:
    """The word right before ``start`` when only spaces separate them."""

    found = _PREVIOUS_WORD.search(text, max(0, start - 40), start)
    return found.group(1) if found else None


def _word_after(text: str, end: int) -> str | None:
    """The word right after ``end`` when only spaces separate them."""

    found = _NEXT_WORD.match(text, end, end + 40)
    return found.group(1) if found else None


def _exact_context_ok(text: str, start: int, end: int, form: str) -> bool:
    """Whether an exact alias at ``text[start:end]`` names the skill in this context."""

    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    if before in _EXACT_BLOCKERS or after in _EXACT_BLOCKERS:
        return False
    previous_word = _word_before(text, start)
    next_word = _word_after(text, end)
    if len(form) == 1:
        if before == "(" and after == ")":
            return False  # (C) copyright, (R) registered trademark.
        if _INITIAL.match(text, end) or _AMPERSAND.match(text, end):
            return False  # "R. Smith", "R & D".
        if previous_word and previous_word.lower() in _LETTER_LABELS:
            return False
        if previous_word and next_word and previous_word.istitle() and next_word.istitle():
            return False  # A middle initial: "Mary R Smith".
    if next_word and next_word.lower() in _REJECT_NEXT.get(form, frozenset()):
        return False
    if previous_word and previous_word.lower() in _REJECT_PREVIOUS.get(form, frozenset()):
        return False
    return not (form in _NAME_LIKE and next_word is not None and next_word.istitle())


def _resolve(text: str, start: int, end: int) -> str | None:
    """Canonical skill for the scanner match ``text[start:end]``, or None."""

    surface = text[start:end]
    if surface in _EXACT:
        return _EXACT[surface] if _exact_context_ok(text, start, end, surface) else None
    candidates = [surface]
    if surface[-1:] in {"s", "S"}:
        candidates.append(surface[:-1])
    candidates.append(_VERSION_SUFFIX.sub("", surface))
    for candidate in candidates:
        skill = _FOLDED.get(_fold(candidate))
        if skill is not None:
            return skill
    return None


def extract_skills(text: str) -> list[str]:
    """Return the canonical skills mentioned in ``text``.

    Args:
        text: Free-form resume or job text (plain text; HTML should be stripped first).

    Returns:
        Distinct canonical skill names in order of first mention.
    """

    found: dict[str, None] = {}
    lowered = text.translate(_ASCII_LOWER)
    position = 0
    while (match := _SCANNER.search(lowered, position)) is not None:
        start, end = match.span()
        left = text[start - 1] if start else ""
        if left.isalnum() or left == "_" or left in _LEFT_JOINERS:
            position = start + 1
            continue
        skill = _resolve(text, start, end)
        if skill is not None:
            found.setdefault(skill, None)
        position = end
    return list(found)


def implied_skills(skills: Iterable[str]) -> dict[str, list[str]]:
    """Map each skill implied by ``skills`` (and not among them) to what implies it.

    Args:
        skills: Canonical skill names found in a resume.

    Returns:
        ``{implied skill: sorted list of the given skills that imply it}``, sorted by key.
    """

    given = set(skills)
    implied: dict[str, set[str]] = {}
    for skill in given:
        for target in _IMPLIES.get(skill, frozenset()):
            if target not in given:
                implied.setdefault(target, set()).add(skill)
    return {target: sorted(implied[target]) for target in sorted(implied)}
