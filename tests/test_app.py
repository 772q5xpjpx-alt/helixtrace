from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_streamlit_app_renders_complete_default_experiment(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    app = AppTest.from_file("app.py", default_timeout=15).run()

    assert not app.exception
    assert not app.error
    assert any("Recover the signal" in block.value for block in app.markdown)
    assert not any("{len(result_source)}" in block.value for block in app.markdown)
    assert _button(app, "Generate free guided interpretation")


def test_streamlit_app_reports_invalid_dna_without_crashing():
    app = AppTest.from_file("app.py", default_timeout=15).run()
    app.text_area[0].set_value("ACNX")
    _button(app, "Run experiment").click()
    app.run()

    assert not app.exception
    assert "invalid symbols: N, X" in app.error[0].value


def test_streamlit_app_guided_interpretation_needs_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file("app.py", default_timeout=15).run()
    _button(app, "Generate free guided interpretation").click()
    app.run()

    assert not app.exception
    assert any("Reliability warning" in block.value for block in app.markdown)
    assert not app.warning
