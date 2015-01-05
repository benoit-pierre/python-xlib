#! /bin/bash

set -x

find_pkgver()
{
  set +x

  tag_version=''
  tag_timestamp=0

  # Find more recent subversion tag commit whose parent is part of the current branch history.
  for branch in `git branch --all --list 'svn/tags/*' --no-color --no-column`
  do
    # Extract version.
    version="$(echo -n "$branch" | sed -n '/.*\/tags\/xlib_\([0-9_]\+\(rc[0-9]\)\?\)$/!Q1;s//\1/;s/_/./g;p')"
    if [ 0 -ne $? ]
    then
      continue
    fi
    # Is parent of tag commit merged?
    if [ 0 -ne "$(git rev-list --count "$branch^" '^HEAD')" ]
    then
      continue
    fi
    # Yes! Retrieve the tag timestamp (date of the tag commit).
    timestamp="$(git --no-pager log -1 --pretty="tformat:%at" "$branch")"
    # Is it more recent?
    if [ "$timestamp" -le "$tag_timestamp" ]
    then
      continue
    fi
    # Yes! We found a new best candidate.
    # Calculate number of additional commits.
    commits="$(git rev-list --count "$branch^..")"
    if [ "$commits" -ge 0 ]
    then
      tag_version="$version.$commits"
    else
      tag_version="$version"
    fi
    tag_timestamp="$timestamp"
  done

  if [ -z "$tag_version" ]
  then
    # No tag found...
    return 1
  fi

  echo "$tag_version"
}

[ -r "$HOME/.makepkg.conf" ] && . "$HOME/.makepkg.conf"

cd "$(dirname "$0")" &&
. ./PKGBUILD &&
pkgver="$(find_pkgver)" &&
src="src/$pkgbase-$pkgver" &&
rm -rf src pkg &&
mkdir -p "$src" &&
sed "s/^pkgver=.*\$/pkgver=$pkgver/" PKGBUILD >PKGBUILD.tmp &&
(cd "$OLDPWD" && git ls-files -z | xargs -0 cp -a --no-dereference --parents --target-directory="$OLDPWD/$src") &&
export PACKAGER="${PACKAGER:-`git config user.name` <`git config user.email`>}" &&
makepkg --noextract --force -p PKGBUILD.tmp &&
rm -rf src pkg PKGBUILD.tmp &&
sudo pacman -U --noconfirm "$pkgname-$pkgver-$pkgrel-any${PKGEXT:-.pkg.tar.xz}"

