#include "opr2/data_validation.hpp"

#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <system_error>

namespace {

constexpr std::array<const char*, 4> kArchives{
    "pr2_arcd.cpr", "pr2_arcs.cpr", "pr2_arct.cpr", "pr2_loca.cpr"};
constexpr char kSignature[] = "ASCARON_";

class TempDirectory {
public:
    TempDirectory() {
        const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
        path_ = std::filesystem::temp_directory_path() /
                ("opr2-test-" + std::to_string(stamp));
        std::filesystem::create_directories(path_);
    }
    ~TempDirectory() {
        std::error_code ignored;
        std::filesystem::remove_all(path_, ignored);
    }
    [[nodiscard]] const std::filesystem::path& path() const { return path_; }

private:
    std::filesystem::path path_;
};

void write_archive(const std::filesystem::path& path, bool valid = true) {
    std::ofstream output(path, std::ios::binary);
    if (valid) {
        output.write(kSignature, sizeof(kSignature) - 1);
        output << "synthetic test payload";
    } else {
        output << "bad";
    }
}

void populate(const std::filesystem::path& directory) {
    for (const char* archive : kArchives) {
        write_archive(directory / archive);
    }
}

bool require(bool condition, const std::string& message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        return false;
    }
    return true;
}

} // namespace

int main() {
    bool passed = true;

    {
        TempDirectory temporary;
        populate(temporary.path());
        const auto result = opr2::validate_data_directory(temporary.path());
        passed &= require(result.ok(), "accepts four synthetic archives with CPR signature");
        passed &= require(result.valid_files.size() == 4, "reports all valid archives");
    }

    {
        TempDirectory temporary;
        populate(temporary.path());
        std::filesystem::remove(temporary.path() / kArchives[1]);
        const auto result = opr2::validate_data_directory(temporary.path());
        passed &= require(!result.ok(), "rejects missing archive");
        passed &= require(result.problems.size() == 1, "reports the missing archive");
    }

    {
        TempDirectory temporary;
        populate(temporary.path());
        write_archive(temporary.path() / kArchives[2], false);
        const auto result = opr2::validate_data_directory(temporary.path());
        passed &= require(!result.ok(), "rejects malformed or truncated signature");
        passed &= require(result.problems.size() == 1, "reports malformed archive");
    }

    {
        TempDirectory temporary;
        populate(temporary.path());
        std::filesystem::remove(temporary.path() / kArchives[3]);
        std::filesystem::create_directory(temporary.path() / kArchives[3]);
        const auto result = opr2::validate_data_directory(temporary.path());
        passed &= require(!result.ok(), "rejects directory where archive file is expected");
    }

    {
        TempDirectory temporary;
        populate(temporary.path());
        const auto target = temporary.path() / "target.cpr";
        write_archive(target);
        std::error_code ec;
        std::filesystem::remove(temporary.path() / kArchives[0]);
        std::filesystem::create_symlink(target, temporary.path() / kArchives[0], ec);
        if (!ec) {
            const auto result = opr2::validate_data_directory(temporary.path());
            passed &= require(result.ok(), "accepts a symlink to a readable regular archive");
        } else {
            std::cout << "SKIP: symlink case unavailable: " << ec.message() << '\n';
        }
    }

    if (passed) {
        std::cout << "all synthetic data validation tests passed\n";
        return 0;
    }
    return 1;
}
