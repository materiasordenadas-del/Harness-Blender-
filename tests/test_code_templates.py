import pytest

from harness_blender import code_templates


def test_primitive_allowlist_blocks_unknown_operator():
    with pytest.raises(ValueError):
        code_templates.create_primitive("monkey_with_shell", "bad", [0, 0, 0], [1, 1, 1])


def test_object_names_are_inserted_as_literals():
    malicious = 'x"; import os; os.remove("bad") #'
    code = code_templates.inspect_object(malicious)
    assert repr(malicious) in code
    compile(code, "<template>", "exec")


def test_transform_requires_valid_three_vectors():
    with pytest.raises(ValueError):
        code_templates.transform_object("Cube", [1, 2], None, None)


@pytest.mark.parametrize(
    "builder",
    [
        code_templates.ping,
        code_templates.inspect_scene,
        lambda: code_templates.inspect_object("Cube"),
        lambda: code_templates.create_primitive("cube", "Cube", [0, 0, 0], [1, 1, 1]),
        lambda: code_templates.transform_object("Cube", [1, 2, 3], [0, 90, 0], [1, 1, 1]),
        lambda: code_templates.delete_object("Cube"),
        lambda: code_templates.validate_mesh("Cube"),
        lambda: code_templates.save_blend(None),
        code_templates.undo,
        lambda: code_templates.capture_screen("/tmp/test.png"),
    ],
)
def test_generated_templates_compile(builder):
    compile(builder(), "<template>", "exec")
