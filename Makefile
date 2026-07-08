.PHONY: test

# Run the whole test suite (stdlib unittest; no dependencies).
test:
	python -m unittest discover -p 'test_*.py'
