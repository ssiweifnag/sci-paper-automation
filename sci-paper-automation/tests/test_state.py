from sci_paper_automation.models.state import PaperState


def test_state_to_dict():
    state = PaperState(project_id='p1', topic='demo', paper_path='paper.docx')
    data = state.to_dict()
    assert data['project_id'] == 'p1'
    assert data['status'] == 'initialized'
