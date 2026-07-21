from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def _open_strand_sandbox(app: AppTest) -> AppTest:
    app.radio[0].set_value("Strand sandbox")
    return app.run()


def test_streamlit_app_opens_on_file_recovery(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    app = AppTest.from_file("app.py", default_timeout=15).run()

    assert not app.exception
    assert not app.error
    assert any("Recover files from noisy DNA reads" in block.value for block in app.markdown)
    assert any("Why DNA?" in block.value for block in app.markdown)
    assert _button(app, "Encode, simulate & recover")


def test_streamlit_app_recovers_default_file_with_fast_consensus():
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.selectbox[0].set_value("Alignment consensus · fast")
    _button(app, "Encode, simulate & recover").click()
    app.run(timeout=20)

    assert not app.exception
    assert not app.error
    assert any("Exact file recovered" in block.value for block in app.markdown)
    assert any("SHA-256" in block.value for block in app.markdown)


def test_streamlit_app_reports_invalid_dna_without_crashing():
    app = AppTest.from_file("app.py", default_timeout=15).run()
    _open_strand_sandbox(app)
    assert any("Known source and channel conditions" in block.value for block in app.markdown)
    assert not any("Why DNA?" in block.value for block in app.markdown)

    app.text_area[0].set_value("ACNX")
    _button(app, "Run experiment").click()
    app.run()

    assert not app.exception
    assert "invalid symbols: N, X" in app.error[0].value
    assert not any("Known source and channel conditions" in block.value for block in app.markdown)


def test_streamlit_app_guided_interpretation_needs_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file("app.py", default_timeout=15).run()
    _open_strand_sandbox(app)
    _button(app, "Generate free guided interpretation").click()
    app.run()

    assert not app.exception
    assert any("Reliability warning" in block.value for block in app.markdown)
    assert not app.warning
