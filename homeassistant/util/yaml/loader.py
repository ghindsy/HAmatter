"""Custom loader."""
from collections import OrderedDict
import fnmatch
import logging
import os
import re
import sys
from typing import Any, Dict, Iterator, List, TextIO, TypeVar, Union, cast, overload

from voluptuous.validators import Boolean
import yaml

from homeassistant.exceptions import HomeAssistantError

from .const import _SECRET_NAMESPACE, SCRAP_YAML, SECRET_YAML
from .objects import Input, NodeListClass, NodeStrClass

try:
    import keyring
except ImportError:
    keyring = None

try:
    import credstash
except ImportError:
    credstash = None


# mypy: allow-untyped-calls, no-warn-return-any

JSON_TYPE = Union[List, Dict, str]  # pylint: disable=invalid-name
DICT_T = TypeVar("DICT_T", bound=Dict)  # pylint: disable=invalid-name

_LOGGER = logging.getLogger(__name__)
__SCRAP_CACHE: Dict[str, JSON_TYPE] = {}
__SECRET_CACHE: Dict[str, JSON_TYPE] = {}

CREDSTASH_WARN = False
KEYRING_WARN = False
RE_SCRAPS = re.compile(r"^~scrap\s+(\S+)")


def clear_config_cache() -> None:
    """Clear the config cache.

    Async friendly.
    """
    __SCRAP_CACHE.clear()
    __SECRET_CACHE.clear()


class SafeLineLoader(yaml.SafeLoader):
    """Loader class that keeps track of line numbers."""

    def compose_node(self, parent: yaml.nodes.Node, index: int) -> yaml.nodes.Node:
        """Annotate a node with the first line it was seen."""
        last_line: int = self.line
        node: yaml.nodes.Node = super().compose_node(parent, index)
        node.__line__ = last_line + 1  # type: ignore
        return node


def load_yaml(fname: str) -> JSON_TYPE:
    """Load a YAML file."""
    try:
        with open(fname, encoding="utf-8") as conf_file:
            parsed = parse_yaml(conf_file)
            # to prevent recursion, scrap files are parsed
            # separately by _load_scrap_yaml below.
            if os.path.basename(fname) != SCRAP_YAML:
                parsed = transform_scraps(os.path.dirname(fname), parsed)
            return parsed
    except UnicodeDecodeError as exc:
        _LOGGER.error("Unable to read file %s: %s", fname, exc)
        raise HomeAssistantError(exc) from exc


def parse_yaml(content: Union[str, TextIO]) -> JSON_TYPE:
    """Load a YAML file."""
    try:
        # If configuration file is empty YAML returns None
        # We convert that to an empty dict
        return yaml.load(content, Loader=SafeLineLoader) or OrderedDict()
    except yaml.YAMLError as exc:
        _LOGGER.error(str(exc))
        raise HomeAssistantError(exc) from exc


@overload
def _add_reference(
    obj: Union[list, NodeListClass], loader: yaml.SafeLoader, node: yaml.nodes.Node
) -> NodeListClass:
    ...


@overload
def _add_reference(
    obj: Union[str, NodeStrClass], loader: yaml.SafeLoader, node: yaml.nodes.Node
) -> NodeStrClass:
    ...


@overload
def _add_reference(
    obj: DICT_T, loader: yaml.SafeLoader, node: yaml.nodes.Node
) -> DICT_T:
    ...


def _add_reference(obj, loader: SafeLineLoader, node: yaml.nodes.Node):  # type: ignore
    """Add file reference information to an object."""
    if isinstance(obj, list):
        obj = NodeListClass(obj)
    if isinstance(obj, str):
        obj = NodeStrClass(obj)
    setattr(obj, "__config_file__", loader.name)
    setattr(obj, "__line__", node.start_mark.line)
    return obj


def _include_yaml(loader: SafeLineLoader, node: yaml.nodes.Node) -> JSON_TYPE:
    """Load another YAML file and embeds it using the !include tag.

    Example:
        device_tracker: !include device_tracker.yaml

    """
    fname = os.path.join(os.path.dirname(loader.name), node.value)
    try:
        return _add_reference(load_yaml(fname), loader, node)
    except FileNotFoundError as exc:
        raise HomeAssistantError(
            f"{node.start_mark}: Unable to read file {fname}."
        ) from exc


def _is_file_valid(name: str) -> bool:
    """Decide if a file is valid."""
    return not name.startswith(".")


def _find_files(directory: str, pattern: str) -> Iterator[str]:
    """Recursively load files in a directory."""
    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if _is_file_valid(d)]
        for basename in sorted(files):
            if _is_file_valid(basename) and fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def _include_dir_named_yaml(
    loader: SafeLineLoader, node: yaml.nodes.Node
) -> OrderedDict:
    """Load multiple files from directory as a dictionary."""
    mapping: OrderedDict = OrderedDict()
    loc = os.path.join(os.path.dirname(loader.name), node.value)
    for fname in _find_files(loc, "*.yaml"):
        filename = os.path.splitext(os.path.basename(fname))[0]
        if os.path.basename(fname) in (SCRAP_YAML, SECRET_YAML):
            continue
        mapping[filename] = load_yaml(fname)
    return _add_reference(mapping, loader, node)


def _include_dir_merge_named_yaml(
    loader: SafeLineLoader, node: yaml.nodes.Node
) -> OrderedDict:
    """Load multiple files from directory as a merged dictionary."""
    mapping: OrderedDict = OrderedDict()
    loc = os.path.join(os.path.dirname(loader.name), node.value)
    for fname in _find_files(loc, "*.yaml"):
        if os.path.basename(fname) in (SCRAP_YAML, SECRET_YAML):
            continue
        loaded_yaml = load_yaml(fname)
        if isinstance(loaded_yaml, dict):
            mapping.update(loaded_yaml)
    return _add_reference(mapping, loader, node)


def _include_dir_list_yaml(
    loader: SafeLineLoader, node: yaml.nodes.Node
) -> List[JSON_TYPE]:
    """Load multiple files from directory as a list."""
    loc = os.path.join(os.path.dirname(loader.name), node.value)
    return [
        load_yaml(f)
        for f in _find_files(loc, "*.yaml")
        if os.path.basename(f) not in (SCRAP_YAML, SECRET_YAML)
    ]


def _include_dir_merge_list_yaml(
    loader: SafeLineLoader, node: yaml.nodes.Node
) -> JSON_TYPE:
    """Load multiple files from directory as a merged list."""
    loc: str = os.path.join(os.path.dirname(loader.name), node.value)
    merged_list: List[JSON_TYPE] = []
    for fname in _find_files(loc, "*.yaml"):
        if os.path.basename(fname) in (SCRAP_YAML, SECRET_YAML):
            continue
        loaded_yaml = load_yaml(fname)
        if isinstance(loaded_yaml, list):
            merged_list.extend(loaded_yaml)
    return _add_reference(merged_list, loader, node)


def _ordered_dict(loader: SafeLineLoader, node: yaml.nodes.MappingNode) -> OrderedDict:
    """Load YAML mappings into an ordered dictionary to preserve key order."""
    loader.flatten_mapping(node)
    nodes = loader.construct_pairs(node)

    seen: Dict = {}
    for (key, _), (child_node, _) in zip(nodes, node.value):
        line = child_node.start_mark.line

        try:
            hash(key)
        except TypeError as exc:
            fname = getattr(loader.stream, "name", "")
            raise yaml.MarkedYAMLError(
                context=f'invalid key: "{key}"',
                context_mark=yaml.Mark(fname, 0, line, -1, None, None),
            ) from exc

        if key in seen:
            fname = getattr(loader.stream, "name", "")
            _LOGGER.warning(
                'YAML file %s contains duplicate key "%s". Check lines %d and %d',
                fname,
                key,
                seen[key],
                line,
            )
        seen[key] = line

    return _add_reference(OrderedDict(nodes), loader, node)


def _construct_seq(loader: SafeLineLoader, node: yaml.nodes.Node) -> JSON_TYPE:
    """Add line number and file name to Load YAML sequence."""
    (obj,) = loader.construct_yaml_seq(node)
    return _add_reference(obj, loader, node)


def _env_var_yaml(loader: SafeLineLoader, node: yaml.nodes.Node) -> str:
    """Load environment variables and embed it into the configuration YAML."""
    args = node.value.split()

    # Check for a default value
    if len(args) > 1:
        return os.getenv(args[0], " ".join(args[1:]))
    if args[0] in os.environ:
        return os.environ[args[0]]
    _LOGGER.error("Environment variable %s not defined", node.value)
    raise HomeAssistantError(node.value)


def _has_scraps(parsed: Any) -> Boolean:
    """See if YAML has any scraps to be resolved."""
    if isinstance(parsed, dict):
        for value in parsed.values():
            if _has_scraps(value):
                return True
    if isinstance(parsed, list):
        for item in parsed:
            if _has_scraps(item):
                return True
    if isinstance(parsed, str):
        if RE_SCRAPS.match(parsed):
            return True
    return False


def _load_scrap_yaml(scrap_path: str) -> Dict[str, JSON_TYPE]:
    """Load the scraps yaml from path."""
    scrap_path = os.path.join(scrap_path, SCRAP_YAML)
    if scrap_path in __SCRAP_CACHE:
        # scraps should always be a string key -> JSON dict.
        return cast(Dict[str, JSON_TYPE], __SCRAP_CACHE[scrap_path])

    _LOGGER.debug("Loading %s", scrap_path)
    try:
        # scraps should always be a string key -> JSON dict.
        scraps = cast(Dict[str, JSON_TYPE], load_yaml(scrap_path))
        if not isinstance(scraps, dict):
            raise HomeAssistantError("Scraps %s is not a dictionary", scrap_path)
    except FileNotFoundError:
        scraps = {}

    # prevent a recursive load above by temporarily loading the raw scraps.
    __SCRAP_CACHE[scrap_path] = scraps
    # when processing scrap files, scraps can refer to other scraps. this
    # has the potential of creating an endless loop if two scraps include
    # each other, so limit the number of times we're willing to keep trying
    # to resolve all the scraps.
    for i in range(5):
        scraps = cast(
            # scraps should always be a string key -> JSON dict.
            Dict[str, JSON_TYPE],
            transform_scraps(os.path.dirname(scrap_path), scraps),
        )
        __SCRAP_CACHE[scrap_path] = scraps
        if not _has_scraps(scraps):
            break
        if i == 4:
            raise HomeAssistantError(
                f"Scrap resolution loop detected while transforming {scrap_path}"
            )
    return scraps


def _resolve_scrap(scrap_path: str, scrap_name: str) -> JSON_TYPE:
    """Locate the scrap being asked for."""
    if (
        scrap_path == os.path.dirname(sys.path[0])
        or not os.path.exists(scrap_path)
        or len(scrap_path) < 5
    ):
        raise HomeAssistantError(f"Scrap '{scrap_name}' not defined")

    scraps = _load_scrap_yaml(scrap_path)

    if scrap_name in scraps:
        _LOGGER.debug(
            "Scrap '%s' retrieved from file %s/%s",
            scrap_name,
            scrap_path,
            SCRAP_YAML,
        )
        return scraps[scrap_name]

    # couldn't find it this dir, bump up to parent dir.
    return _resolve_scrap(os.path.dirname(scrap_path), scrap_name)


def transform_scraps(fname: str, parsed: Any) -> JSON_TYPE:
    """Process YAML scraps into config."""
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            parsed[key] = transform_scraps(fname, value)
    if isinstance(parsed, list):
        new_parsed = []
        for item in parsed:
            new_item = transform_scraps(fname, item)
            if isinstance(new_item, list):
                new_parsed.extend(new_item)
            else:
                new_parsed.append(new_item)
        parsed = new_parsed
    if isinstance(parsed, str):
        p = RE_SCRAPS.match(parsed)
        if p is not None:
            parsed = _resolve_scrap(fname, p.group(1))
    return parsed


def _load_secret_yaml(secret_path: str) -> JSON_TYPE:
    """Load the secrets yaml from path."""
    secret_path = os.path.join(secret_path, SECRET_YAML)
    if secret_path in __SECRET_CACHE:
        return __SECRET_CACHE[secret_path]

    _LOGGER.debug("Loading %s", secret_path)
    try:
        secrets = load_yaml(secret_path)
        if not isinstance(secrets, dict):
            raise HomeAssistantError("Secrets is not a dictionary")
        if "logger" in secrets:
            logger = str(secrets["logger"]).lower()
            if logger == "debug":
                _LOGGER.setLevel(logging.DEBUG)
            else:
                _LOGGER.error(
                    "secrets.yaml: 'logger: debug' expected, but 'logger: %s' found",
                    logger,
                )
            del secrets["logger"]
    except FileNotFoundError:
        secrets = {}
    __SECRET_CACHE[secret_path] = secrets
    return secrets


def secret_yaml(loader: SafeLineLoader, node: yaml.nodes.Node) -> JSON_TYPE:
    """Load secrets and embed it into the configuration YAML."""
    secret_path = os.path.dirname(loader.name)
    while True:
        secrets = _load_secret_yaml(secret_path)

        if node.value in secrets:
            _LOGGER.debug(
                "Secret %s retrieved from secrets.yaml in folder %s",
                node.value,
                secret_path,
            )
            return secrets[node.value]

        if secret_path == os.path.dirname(sys.path[0]):
            break  # sys.path[0] set to config/deps folder by bootstrap

        secret_path = os.path.dirname(secret_path)
        if not os.path.exists(secret_path) or len(secret_path) < 5:
            break  # Somehow we got past the .homeassistant config folder

    if keyring:
        # do some keyring stuff
        pwd = keyring.get_password(_SECRET_NAMESPACE, node.value)
        if pwd:
            global KEYRING_WARN  # pylint: disable=global-statement

            if not KEYRING_WARN:
                KEYRING_WARN = True
                _LOGGER.warning(
                    "Keyring is deprecated and will be removed in March 2021."
                )

            _LOGGER.debug("Secret %s retrieved from keyring", node.value)
            return pwd

    global credstash  # pylint: disable=invalid-name, global-statement

    if credstash:
        # pylint: disable=no-member
        try:
            pwd = credstash.getSecret(node.value, table=_SECRET_NAMESPACE)
            if pwd:
                global CREDSTASH_WARN  # pylint: disable=global-statement

                if not CREDSTASH_WARN:
                    CREDSTASH_WARN = True
                    _LOGGER.warning(
                        "Credstash is deprecated and will be removed in March 2021."
                    )
                _LOGGER.debug("Secret %s retrieved from credstash", node.value)
                return pwd
        except credstash.ItemNotFound:
            pass
        except Exception:  # pylint: disable=broad-except
            # Catch if package installed and no config
            credstash = None

    raise HomeAssistantError(f"Secret {node.value} not defined")


yaml.SafeLoader.add_constructor("!include", _include_yaml)
yaml.SafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _ordered_dict
)
yaml.SafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, _construct_seq
)
yaml.SafeLoader.add_constructor("!env_var", _env_var_yaml)
yaml.SafeLoader.add_constructor("!secret", secret_yaml)
yaml.SafeLoader.add_constructor("!include_dir_list", _include_dir_list_yaml)
yaml.SafeLoader.add_constructor("!include_dir_merge_list", _include_dir_merge_list_yaml)
yaml.SafeLoader.add_constructor("!include_dir_named", _include_dir_named_yaml)
yaml.SafeLoader.add_constructor(
    "!include_dir_merge_named", _include_dir_merge_named_yaml
)
yaml.SafeLoader.add_constructor("!input", Input.from_node)
