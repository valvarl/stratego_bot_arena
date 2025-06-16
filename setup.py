from setuptools import setup, find_packages

setup(
    name="bot_arena",
    version="0.1.0",
    description="A Stratego bot arena module",
    author="Valery Varlachev",
    author_email="valvarl@ya.ru",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # здесь можно указать зависимости, например:
        # 'numpy>=1.21.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",
)