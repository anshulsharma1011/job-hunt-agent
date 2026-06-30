import pytest

from config.app_config import AppConfig
from sources.naukri import NaukriSource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer"],
    locations=["Bangalore"],
    remote=False,
)

_SAMPLE_HTML = """
<div>
  <article class="jobTuple">
    <a class="title" href="https://www.naukri.com/job-1">Senior Backend Engineer</a>
    <a class="subTitle">Razorpay</a>
    <ul><li class="location"><span>Bangalore</span></li></ul>
  </article>
  <article class="jobTuple">
    <a class="title" href="https://www.naukri.com/job-2">Python Developer</a>
    <a class="subTitle">Zepto</a>
    <ul><li class="location"><span>Mumbai</span></li></ul>
  </article>
</div>
"""


def test_fetch_raises_not_implemented(app_config: AppConfig) -> None:
    source = NaukriSource(app_config)
    with pytest.raises(NotImplementedError):
        source.fetch(_CRITERIA)


def test_parse_from_html_returns_opportunities(app_config: AppConfig) -> None:
    source = NaukriSource(app_config)
    results = source.parse_from_html(_SAMPLE_HTML)

    assert len(results) == 2
    assert results[0].source == "naukri"
    assert results[0].role_title == "Senior Backend Engineer"
    assert results[0].company == "Razorpay"
    assert results[0].location == "Bangalore"
    assert results[1].role_title == "Python Developer"


def test_parse_from_html_skips_cards_without_title_or_link(app_config: AppConfig) -> None:
    html = """
    <article class="jobTuple">
      <a class="subTitle">Some Company</a>
    </article>
    """
    source = NaukriSource(app_config)
    results = source.parse_from_html(html)
    assert results == []


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    source = NaukriSource(app_config)
    assert source.is_enabled(app_config) is True
