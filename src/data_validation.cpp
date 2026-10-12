#include "opr2/data_validation.hpp"

#include <array>
#include <fstream>
#include <system_error>

namespace opr2 {
namespace {

constexpr std::array<char, 8> kCprSignature{'A', 'S', 'C', 'A', 'R', 'O', 'N', '_'};
constexpr std::array<const char*, 4> kRequiredArchives{
    "pr2_arcd.cpr", "pr2_arcs.cpr", "pr2_arct.cpr", "pr2_loca.cpr"};

} // namespace

DataValidationResult validate_data_directory(const std::filesystem::path& directory) {
    DataValidationResult result;

    for (const char* filename : kRequiredArchives) {
        const auto path = directory / filename;
        std::error_code ec;
        const auto status = std::filesystem::status(path, ec);
        if (ec || !std::filesystem::exists(status)) {
            result.problems.push_back({path, "required archive is missing or cannot be accessed"});
            continue;
        }
        if (!std::filesystem::is_regular_file(status)) {
            result.problems.push_back({path, "required archive is not a regular file"});
            continue;
        }

        std::ifstream stream(path, std::ios::binary);
        if (!stream) {
            result.problems.push_back({path, "required archive cannot be opened for reading"});
            continue;
        }

        std::array<char, kCprSignature.size()> header{};
        stream.read(header.data(), static_cast<std::streamsize>(header.size()));
        if (stream.gcount() != static_cast<std::streamsize>(header.size()) || header != kCprSignature) {
            result.problems.push_back({path, "invalid CPR signature (expected ASCARON_ header)"});
            continue;
        }
        result.valid_files.push_back(path);
    }

    return result;
}

} // namespace opr2
