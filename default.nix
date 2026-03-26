{
  nixpkgs ?
    import
      (fetchTarball {
        name = "nixpkgs2511";
        url = "https://github.com/NixOS/nixpkgs/archive/25.11.tar.gz";
        sha256 = "sha256:1zn1lsafn62sz6azx6j735fh4vwwghj8cc9x91g5sx2nrg23ap9k";
      })
      {
        config = { };
        overlays = [ ];
      },
  python3Packages ? nixpkgs.python3Packages,
}:
with {
  pkg =
    {
      buildPythonPackage,
      python-dateutil,
      feedparser,
      python,
      setuptools,
    }:
    buildPythonPackage {
      name = "feed2maildirsimple";
      version = "0.4.0";
      src = ./.;
      pyproject = true;
      build-system = [ setuptools ];
      propagatedBuildInputs = [
        python
        python-dateutil
        feedparser
      ];
    };
};
python3Packages.callPackage pkg { }
