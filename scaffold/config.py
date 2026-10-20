import yaml
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_DIR = "~/.config"
CONFIG_FILE = "scaffold.yaml"


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], yaml_file: str = "config.yaml"):
        super().__init__(settings_cls)
        self.yaml_file = yaml_file

    def get_field_value(self, field, field_name):
        return None, field_name, False

    def __call__(self) -> dict:
        try:
            with open(self.yaml_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}


class Settings(BaseSettings):
    app_name: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, str(CONFIG_DIR / CONFIG_FILE))
        )
