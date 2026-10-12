#include "opr2/data_validation.hpp"
#include "opr2/executable_path.hpp"

#include <filesystem>
#include <iostream>
#include <string_view>

namespace {

constexpr int kUsageError = 2;
constexpr int kDataError = 1;

void print_help(std::ostream& output) {
    output << "opr2 " << OPR2_VERSION << " - independent Port Royale 2 bootstrap\n"
           << "Usage: opr2 --check-data [--data-dir PATH]\n"
           << "       opr2 --help\n\n"
           << "Checks for the four required CPR archives. By default, PATH is the directory\n"
           << "containing this executable. Validation reads only each archive's signature.\n";
}

} // namespace

int main(int argc, char* argv[]) {
    bool check_data = false;
    std::filesystem::path data_directory;
    bool data_directory_set = false;

    for (int index = 1; index < argc; ++index) {
        const std::string_view argument(argv[index]);
        if (argument == "--help") {
            if (argc != 2) {
                std::cerr << "--help cannot be combined with other options\n";
                print_help(std::cerr);
                return kUsageError;
            }
            print_help(std::cout);
            return 0;
        }
        if (argument == "--check-data") {
            if (check_data) {
                std::cerr << "--check-data was supplied more than once\n";
                return kUsageError;
            }
            check_data = true;
        } else if (argument == "--data-dir") {
            if (data_directory_set || index + 1 >= argc) {
                std::cerr << "--data-dir requires exactly one PATH\n";
                print_help(std::cerr);
                return kUsageError;
            }
            data_directory = argv[++index];
            data_directory_set = true;
            if (data_directory.empty()) {
                std::cerr << "--data-dir PATH cannot be empty\n";
                return kUsageError;
            }
        } else {
            std::cerr << "unknown option: " << argument << '\n';
            print_help(std::cerr);
            return kUsageError;
        }
    }

    if (!check_data) {
        std::cerr << "missing required option: --check-data\n";
        print_help(std::cerr);
        return kUsageError;
    }

    if (!data_directory_set) {
        const auto executable = opr2::executable_path();
        if (!executable.ok()) {
            std::cerr << "error: " << executable.error << '\n';
            return kDataError;
        }
        data_directory = executable.path.parent_path();
    }

    const auto validation = opr2::validate_data_directory(data_directory);
    if (!validation.ok()) {
        std::cerr << "data validation failed in " << data_directory << ":\n";
        for (const auto& problem : validation.problems) {
            std::cerr << "  " << problem.path.filename().string() << ": " << problem.message << '\n';
        }
        return kDataError;
    }

    std::cout << "data validation passed for " << validation.valid_files.size()
              << " required archives in " << data_directory << '\n';
    return 0;
}
