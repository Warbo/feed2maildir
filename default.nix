{ nixpkgs ? import (fetchTarball {
  name = "nixpkgs2305";
  url = "https://github.com/NixOS/nixpkgs/archive/23.05.tar.gz";
  sha256 = "10wn0l08j9lgqcw8177nh2ljrnxdrpri7bp0g7nvrsn9rkawvlbf";
}) {
  config = { };
  overlays = [ ];
}, python3Packages ? nixpkgs.python3Packages }:
with {
  pkg = { buildPythonPackage, dateutil, feedparser, python }:
    buildPythonPackage {
      name = "feed2maildirsimple";
      version = "0.4.0";
      src = ./.;
      propagatedBuildInputs = [ python dateutil feedparser ];
    };
};
python3Packages.callPackage pkg { }
