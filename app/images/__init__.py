def __getattr__(name):
    if name == "WhiskAPI":
        from .whisk import WhiskAPI
        return WhiskAPI
    if name == "ImageGenerator":
        from .whisk import ImageGenerator
        return ImageGenerator
    if name == "ImageSearch":
        from .search import ImageSearch
        return ImageSearch
    if name == "ImageValidator":
        from .validator import ImageValidator
        return ImageValidator
    if name == "ThumbnailGenerator":
        from .thumbnail import ThumbnailGenerator
        return ThumbnailGenerator
    if name == "ESRGANUpscaler":
        from .upscaler import ESRGANUpscaler
        return ESRGANUpscaler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "WhiskAPI", "ImageGenerator", "ImageSearch",
    "ImageValidator", "ThumbnailGenerator", "ESRGANUpscaler",
]
