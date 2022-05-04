#!/bin/bash

DIRNAME=$(dirname $0)
VERFILE=${DIRNAME}/src/GANESHA_VERSION

# Read GANESHA_VERSION file
. ${VERFILE}
if (( $? != 0 ))
then
    echo "Unable to parse GANESHA_VERSION file. Aborting!!!"
    exit 1
fi

# Detect Ubuntu Code name
if [[ ! -r /etc/os-release ]]
then
    echo "Unable to detect build os. Aborting!!!"
    exit 1
fi
. /etc/os-release

case "${UBUNTU_CODENAME}" in
    focal)
    OS_RELEASE="~${UBUNTU_CODENAME}"
    ;;

    jammy)
    OS_RELEASE="~${UBUNTU_CODENAME}"
    ;;

    *)
    echo "Unsupported build os (${UBUNTU_CODENAME}). Aborting!!!"
    exit 1
esac

GANESHA_VERSION_STRING="$GANESHA_MAJOR_VERSION.$GANESHA_MINOR_VERSION-$GANESHA_TAG$OS_RELEASE"
echo "Ganesha packages with version : $GANESHA_VERSION_STRING will be generated."

#Update the changelog file with new Ganesha version and Ubuntu codename
debchange --newversion $GANESHA_VERSION_STRING --distribution $UBUNTU_CODENAME "NFS Ganesha release $GANESHA_VERSION_STRING for Spectrum Scale" --force-bad-version

rm -r src/debian
echo "Creating build dependencies ..."
mk-build-deps --install debian/control
echo "Building packages ..."
dpkg-buildpackage -b -us -uc

