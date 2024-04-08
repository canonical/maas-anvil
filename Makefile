.DEFAULT_GOAL := snap

SNAPCRAFT := SNAPCRAFT_BUILD_INFO=1 snapcraft -v
SNAP_FILE := maas-anvil.snap

snap:
	$(SNAPCRAFT) -o $(SNAP_FILE)
.PHONY: snap

snap-clean:
	$(SNAPCRAFT) clean
	rm -f $(SNAP_FILE)
.PHONY: snap-clean
